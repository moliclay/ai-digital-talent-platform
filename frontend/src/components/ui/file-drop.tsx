import { useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { Upload, X } from "lucide-react";

import { copy } from "../../content/copy";
import { formatBytes } from "../../lib/format";
import { IconButton } from "./icon-button";
import styles from "./file-drop.module.css";

type FileDropProps = {
  files: File[];
  onChange: (files: File[]) => void;
  accept: string;
  disabled?: boolean;
  hint?: string;
  acceptLabel?: string;
  multiple?: boolean;
};

export function FileDrop({
  files,
  onChange,
  accept,
  disabled = false,
  hint = copy.resumes.dropHint,
  acceptLabel = copy.resumes.dropAccept,
  multiple = true,
}: FileDropProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function append(list: FileList | null) {
    if (!list || list.length === 0) return;
    onChange([...files, ...Array.from(list)]);
  }

  function openPicker() {
    if (disabled) return;
    inputRef.current?.click();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openPicker();
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (disabled) return;
    append(event.dataTransfer.files);
  }

  return (
    <div>
      <div
        className={dragging ? `${styles.zone} ${styles.dragging}` : styles.zone}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled || undefined}
        onClick={openPicker}
        onKeyDown={handleKeyDown}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <Upload size={20} strokeWidth={1.75} className={styles.icon} aria-hidden="true" />
        <p className={styles.hint}>{hint}</p>
        <p className={styles.accept}>{acceptLabel}</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple={multiple}
        accept={accept}
        className="sr-only"
        tabIndex={-1}
        onChange={(event) => {
          append(event.target.files);
          event.target.value = "";
        }}
      />
      {files.length > 0 ? (
        <ul className={styles.list}>
          {files.map((file, index) => (
            <li className={styles.item} key={`${file.name}-${file.size}-${index}`}>
              <span className={styles.name} title={file.name}>
                {file.name}
              </span>
              <span className={styles.size}>{formatBytes(file.size)}</span>
              <IconButton
                label={`${copy.resumes.remove} ${file.name}`}
                onClick={() => onChange(files.filter((_, position) => position !== index))}
              >
                <X size={16} strokeWidth={1.75} aria-hidden="true" />
              </IconButton>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
