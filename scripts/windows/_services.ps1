param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Start', 'Stop')]
    [string]$Mode
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$logs = Join-Path $root 'logs'
$services = @(
    @{ Name = '后端 API'; Port = 8000; Wrapper = (Join-Path $PSScriptRoot '_run_backend.bat'); Log = 'backend.log'; Health = '/api/health' }
    @{ Name = '前端 Web'; Port = 5174; Wrapper = (Join-Path $PSScriptRoot '_run_frontend.bat'); Log = 'frontend.log'; Health = '/' }
)

function Test-Port([int]$Port) {
    return $Port -in [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners().Port
}

function Wait-Port([int]$Port, [int]$Seconds) {
    $timer = [Diagnostics.Stopwatch]::StartNew()
    do {
        if (Test-Port $Port) { return $true }
        Start-Sleep -Milliseconds 500
    } while ($timer.Elapsed.TotalSeconds -lt $Seconds)
    return $false
}

function Get-ServiceState($Service) {
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='cmd.exe' OR Name='python.exe' OR Name='node.exe'")
    $byId = @{}
    foreach ($process in $processes) { $byId[[int]$process.ProcessId] = $process }
    $wrapperPattern = '\s/c\s+""?' + [regex]::Escape($Service.Wrapper) + '""?\s*$'
    $runners = @($processes | Where-Object { $_.Name -eq 'cmd.exe' -and $_.CommandLine -match $wrapperPattern })
    $runnerIds = $runners.ProcessId
    $foreign = @()
    $owned = @()
    if (Test-Port $Service.Port) {
        $listeners = Get-NetTCPConnection -State Listen | Where-Object LocalPort -eq $Service.Port
        foreach ($listenerId in ($listeners.OwningProcess | Select-Object -Unique)) {
            $current = $byId[[int]$listenerId]
            while ($current -and $current.ProcessId -notin $runnerIds) {
                $parent = $byId[[int]$current.ParentProcessId]
                # A reused PID does not identify the original parent.
                if (!$parent -or $parent.CreationDate -gt $current.CreationDate) { $current = $null; break }
                $current = $parent
            }
            if ($current) { $owned += $byId[[int]$listenerId] } else { $foreign += $listenerId }
        }
    }
    return @{ Runners = $runners; Owned = $owned; Foreign = $foreign }
}

function Assert-FreeOrOwned($Service, $State) {
    if ($State.Foreign.Count) {
        throw "$($Service.Name) 端口 $($Service.Port) 已由其他进程占用（PID $($State.Foreign -join ', ')）。"
    }
}

function Stop-Runner([int]$ProcessId) {
    & $env:ComSpec /d /c "taskkill.exe /PID $ProcessId /T /F >nul 2>&1"
}

function Start-Dependencies {
    if (!(Test-Port 3306)) {
        $defaultMysqlHome = 'D:\mysql-9.4.0-winx64'
        $mysqlHome = $defaultMysqlHome
        if ($env:MYSQL_HOME) {
            if (Test-Path -LiteralPath (Join-Path $env:MYSQL_HOME 'bin\mysqld.exe') -PathType Leaf) {
                $mysqlHome = $env:MYSQL_HOME
            } else {
                Write-Warning "MYSQL_HOME 指向的目录没有 mysqld.exe：$env:MYSQL_HOME。尝试使用 $defaultMysqlHome。"
            }
        }
        $mysql = Join-Path $mysqlHome 'bin\mysqld.exe'
        if (!(Test-Path -LiteralPath $mysql -PathType Leaf)) { throw "找不到 MySQL：$mysql。请启动 MySQL 或设置有效的 MYSQL_HOME。" }
        $data = Join-Path $mysqlHome 'data'
        Write-Host "正在启动 MySQL（3306）：$mysql"
        Start-Process -FilePath $mysql -ArgumentList ('--port=3306 --datadir="{0}"' -f $data) -WindowStyle Minimized
        if (!(Wait-Port 3306 40)) { throw 'MySQL 未能在 40 秒内监听 3306。' }
    }
    if (!(Test-Port 6379)) { Write-Warning 'Redis 未监听 6379，应用将使用无缓存模式。' }
    if (!(Test-Port 11434)) {
        $ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue
        if ($ollama) {
            Start-Process -FilePath $ollama.Source -ArgumentList 'serve' -WindowStyle Minimized -RedirectStandardOutput (Join-Path $logs 'ollama.log') -RedirectStandardError (Join-Path $logs 'ollama-error.log')
            if (!(Wait-Port 11434 40)) { Write-Warning 'Ollama 尚未监听 11434。' }
        } else { Write-Warning '找不到 Ollama，语义检索可能不可用。' }
    }
    if (!(Test-Port 19530)) {
        if (Get-Command docker.exe -ErrorAction SilentlyContinue) {
            & cmd.exe /d /c 'docker start milvus26-etcd milvus26-minio milvus26-standalone >nul 2>&1'
            if ($LASTEXITCODE -ne 0 -or !(Wait-Port 19530 60)) { Write-Warning 'Milvus 尚未就绪。' }
        } else { Write-Warning '找不到 Docker，语义检索可能不可用。' }
    }
}

function Test-ServiceReady($Service) {
    $url = "http://127.0.0.1:$($Service.Port)$($Service.Health)"
    try {
        if ($Service.Port -eq 8000) {
            $body = & curl.exe --noproxy '*' --silent --fail --max-time 4 $url
            if ($LASTEXITCODE -ne 0) { return $false }
            $health = $body | ConvertFrom-Json
            return $health.data.mysql -eq $true -and $health.data.status -eq 'ok'
        }
        $status = & curl.exe --noproxy '*' --silent --fail --max-time 4 --output NUL --write-out '%{http_code}' $url
        return $LASTEXITCODE -eq 0 -and $status -eq '200'
    } catch {
        return $false
    }
}

$lock = $null
$launched = @()
$failed = $false
try {
    [IO.Directory]::CreateDirectory($logs) | Out-Null
    try {
        $lock = [IO.File]::Open((Join-Path $logs 'windows-services.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch [IO.IOException] {
        throw '另一个启停操作正在执行，请稍后重试。'
    }
    if ($Mode -eq 'Start') {
        foreach ($service in $services) { Assert-FreeOrOwned $service (Get-ServiceState $service) }
        if (!(Test-Path -LiteralPath (Join-Path $root 'backend\.venv\Scripts\python.exe'))) {
            throw '找不到后端虚拟环境，请按 README 安装后端依赖。'
        }
        if (!(Get-Command node.exe -ErrorAction SilentlyContinue) -or
            !(Test-Path -LiteralPath (Join-Path $root 'frontend\node_modules\vite\bin\vite.js'))) {
            throw '找不到 Node.js 或 Vite，请按 README 安装前端依赖。'
        }
        if (!(Get-Command curl.exe -ErrorAction SilentlyContinue)) { throw '找不到 curl.exe，无法执行 HTTP 就绪检查。' }
        Start-Dependencies
        foreach ($service in $services) {
            $state = Get-ServiceState $service
            Assert-FreeOrOwned $service $state
            $runner = $null
            if (!$state.Runners.Count) {
                Write-Host "正在启动 $($service.Name)（$($service.Port)）..."
                $runner = Start-Process -FilePath $env:ComSpec -ArgumentList ('/d /c ""{0}""' -f $service.Wrapper) -WorkingDirectory $root -WindowStyle Minimized -PassThru
                $launched += $runner
            }
            $timer = [Diagnostics.Stopwatch]::StartNew()
            $ready = $false
            do {
                if ($runner -and $runner.HasExited) { break }
                if (Test-Port $service.Port) {
                    $state = Get-ServiceState $service
                    Assert-FreeOrOwned $service $state
                    if ($state.Owned.Count -and (Test-ServiceReady $service)) { $ready = $true; break }
                }
                Start-Sleep -Milliseconds 400
            } while ($timer.Elapsed.TotalSeconds -lt 60)
            if (!$ready) { throw "$($service.Name) 未就绪，请查看 $(Join-Path $logs $service.Log)。" }
            Write-Host "$($service.Name) 已就绪（$($service.Port)）。"
        }
        Write-Host '启动完成。前端 http://127.0.0.1:5174  接口文档 http://127.0.0.1:8000/docs'
        try { Start-Process 'http://127.0.0.1:5174' } catch { Write-Warning '请手动打开前端地址。' }
    } else {
        foreach ($service in $services[1..0]) {
            $before = Get-ServiceState $service
            foreach ($runner in $before.Runners) {
                $current = Get-CimInstance Win32_Process -Filter "ProcessId=$($runner.ProcessId)"
                if ($current -and $current.CreationDate -eq $runner.CreationDate) { Stop-Runner $runner.ProcessId }
            }
            $after = Get-ServiceState $service
            $remaining = @($before.Owned | Where-Object {
                $current = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ProcessId)"
                $current -and $current.CreationDate -eq $_.CreationDate
            })
            if ($after.Runners.Count -or $remaining.Count) {
                Write-Warning "$($service.Name) 仍有进程运行，请检查权限后重试。"
                $failed = $true
            } elseif ($after.Foreign.Count) {
                Write-Warning "$($service.Name) 的端口 $($service.Port) 由其他进程占用（PID $($after.Foreign -join ', ')），已保留。"
            } else { Write-Host "$($service.Name) 已停止（$($service.Port) 已释放）。" }
        }
        if (!$failed) { Write-Host '停止完成。MySQL、Redis、Ollama 和 Milvus 保持原状态。' }
    }
} catch {
    Write-Host "[错误] $($_.Exception.Message)"
    foreach ($runner in $launched) {
        if (!$runner.HasExited) { Stop-Runner $runner.Id }
    }
    $failed = $true
} finally {
    if ($lock) { $lock.Dispose() }
}
if ($failed) { exit 1 }
exit 0
