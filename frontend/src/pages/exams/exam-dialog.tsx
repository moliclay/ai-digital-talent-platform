import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "../../components/ui/button";
import { FormField } from "../../components/ui/form-field";
import { Input } from "../../components/ui/input";
import { Select } from "../../components/ui/select";
import { Modal } from "../../components/ui/modal";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import styles from "./dialogs.module.css";
import type { Audience, Bank, CreateExamResult } from "./types";

const text = copy.exams;

type ExamDialogProps = {
  open: boolean;
  banks: Bank[];
  initialAudience: Audience;
  onClose: () => void;
  onCreated: (result: CreateExamResult) => void;
};

export function ExamDialog({ open, banks, initialAudience, onClose, onCreated }: ExamDialogProps) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [audience, setAudience] = useState<Audience>(initialAudience);
  const [selected, setSelected] = useState<number[]>([]);
  const [count, setCount] = useState("5");
  const [pass, setPass] = useState("60");
  const [duration, setDuration] = useState("60");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!open) return;
    setAudience(initialAudience);
    setSelected([]);
    setNotice("");
  }, [open, initialAudience]);

  const eligibleBanks = banks.filter((bank) => bank.audience === audience);
  const poolTotal = eligibleBanks
    .filter((bank) => selected.includes(bank.id))
    .reduce((sum, bank) => sum + bank.total_questions, 0);

  function toggle(id: number) {
    setSelected((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  }

  const create = useMutation({
    mutationFn: () =>
      request<CreateExamResult>("/exams", {
        method: "POST",
        body: {
          name,
          category,
          audience,
          bank_ids: selected,
          question_count: Number(count),
          pass_score: Number(pass),
          duration_minutes: Number(duration),
        },
      }),
    onSuccess: (result) => {
      setName("");
      setCategory("");
      setSelected([]);
      onCreated(result);
    },
    onError: (error) =>
      setNotice(`${text.createError}${error instanceof ApiError ? error.message : text.loadErrorHint}`),
  });

  const canSubmit = name.trim() && selected.length > 0 && Number(count) >= 1;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={text.examDialogTitle}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={create.isPending}>
            {copy.common.cancel}
          </Button>
          <Button
            variant="primary"
            loading={create.isPending}
            disabled={!canSubmit}
            onClick={() => create.mutate()}
          >
            {text.confirm}
          </Button>
        </>
      }
    >
      <div className={styles.stack}>
        <div className={styles.row}>
          <FormField id="exam-name" label={text.eName}>
            <Input
              value={name}
              placeholder={text.eNamePlaceholder}
              onChange={(event) => setName(event.target.value)}
            />
          </FormField>
          <FormField id="exam-category" label={text.eCategory}>
            <Input
              value={category}
              placeholder={text.eCategoryPlaceholder}
              onChange={(event) => setCategory(event.target.value)}
            />
          </FormField>
        </div>

        <FormField id="exam-audience" label={text.audienceLabel}>
          <Select
            id="exam-audience"
            value={audience}
            options={[
              { value: "candidate", label: copy.common.audience.candidate },
              { value: "employee", label: copy.common.audience.employee },
            ]}
            onChange={(value) => {
              setAudience(value as Audience);
              setSelected([]);
            }}
            ariaLabel={text.audienceLabel}
          />
        </FormField>

        <fieldset className={styles.fieldset}>
          <legend className={styles.legend}>{text.eBanks}</legend>
          <div className={styles.bankList}>
            {eligibleBanks.map((bank) => (
              <label className={styles.check} key={bank.id}>
                <input
                  type="checkbox"
                  checked={selected.includes(bank.id)}
                  onChange={() => toggle(bank.id)}
                />
                <span className={styles.checkText}>
                  <span className={styles.checkLabel}>{bank.name}</span>
                  <span className={styles.checkMeta}>{text.bankCount(bank.total_questions)}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className={styles.row}>
          <FormField id="exam-count" label={text.eCount}>
            <Input
              type="number"
              min="1"
              value={count}
              onChange={(event) => setCount(event.target.value)}
            />
          </FormField>
          <FormField id="exam-pass" label={text.ePass}>
            <Input
              type="number"
              min="0"
              value={pass}
              onChange={(event) => setPass(event.target.value)}
            />
          </FormField>
          <FormField id="exam-duration" label={text.eDuration}>
            <Input
              type="number"
              min="1"
              value={duration}
              onChange={(event) => setDuration(event.target.value)}
            />
          </FormField>
        </div>
        {selected.length > 0 ? <p className={styles.hint}>{text.eCountHint(poolTotal)}</p> : null}
        {notice ? <p className={styles.error}>{notice}</p> : null}
      </div>
    </Modal>
  );
}
