import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "../../components/ui/button";
import { FormField } from "../../components/ui/form-field";
import { Input } from "../../components/ui/input";
import { Modal } from "../../components/ui/modal";
import { Select } from "../../components/ui/select";
import { Textarea } from "../../components/ui/textarea";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import styles from "./dialogs.module.css";
import type { Audience, CreateBankResult } from "./types";

const text = copy.exams;

type BankDialogProps = {
  open: boolean;
  initialAudience: Audience;
  onClose: () => void;
  onCreated: () => void;
};

export function BankDialog({ open, initialAudience, onClose, onCreated }: BankDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [audience, setAudience] = useState<Audience>("candidate");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (open) setAudience(initialAudience);
  }, [open, initialAudience]);

  const create = useMutation({
    mutationFn: () =>
      request<CreateBankResult>("/question-banks", {
        method: "POST",
        body: { name, description, audience },
      }),
    onSuccess: () => {
      setName("");
      setDescription("");
      setAudience("candidate");
      onCreated();
    },
    onError: (error) =>
      setNotice(`${text.createError}${error instanceof ApiError ? error.message : text.loadErrorHint}`),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={text.bankDialogTitle}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={create.isPending}>
            {copy.common.cancel}
          </Button>
          <Button
            variant="primary"
            loading={create.isPending}
            disabled={!name.trim()}
            onClick={() => create.mutate()}
          >
            {text.confirm}
          </Button>
        </>
      }
    >
      <div className={styles.stack}>
        <FormField id="bank-name" label={text.bankName}>
          <Input
            value={name}
            placeholder={text.bankNamePlaceholder}
            onChange={(event) => setName(event.target.value)}
          />
        </FormField>
        <FormField id="bank-audience" label={text.audienceLabel}>
          <Select
            id="bank-audience"
            value={audience}
            options={[
              { value: "candidate", label: copy.common.audience.candidate },
              { value: "employee", label: copy.common.audience.employee },
            ]}
            onChange={(value) => setAudience(value as Audience)}
            ariaLabel={text.audienceLabel}
          />
        </FormField>
        <FormField id="bank-desc" label={text.bankDesc}>
          <Textarea
            value={description}
            placeholder={text.bankDescPlaceholder}
            onChange={(event) => setDescription(event.target.value)}
          />
        </FormField>
        {notice ? <p className={styles.error}>{notice}</p> : null}
      </div>
    </Modal>
  );
}
