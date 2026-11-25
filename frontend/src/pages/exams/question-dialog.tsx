import { useState } from "react";
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
import type { Bank, CreateQuestionResult } from "./types";

const text = copy.exams;

type QuestionDialogProps = {
  open: boolean;
  banks: Bank[];
  onClose: () => void;
  onCreated: () => void;
};

const TYPE_OPTIONS = (Object.keys(text.questionTypes) as Array<keyof typeof text.questionTypes>).map(
  (value) => ({ value, label: text.questionTypes[value] }),
);

const DIFFICULTY_OPTIONS = (Object.keys(text.difficulty) as Array<keyof typeof text.difficulty>).map(
  (value) => ({ value, label: text.difficulty[value] }),
);

export function QuestionDialog({ open, banks, onClose, onCreated }: QuestionDialogProps) {
  const [bankId, setBankId] = useState("");
  const [type, setType] = useState("single_choice");
  const [content, setContent] = useState("");
  const [optionsText, setOptionsText] = useState("");
  const [answer, setAnswer] = useState("");
  const [score, setScore] = useState("10");
  const [difficulty, setDifficulty] = useState("medium");
  const [knowledge, setKnowledge] = useState("");
  const [category, setCategory] = useState("");
  const [notice, setNotice] = useState("");

  const create = useMutation({
    mutationFn: () =>
      request<CreateQuestionResult>("/questions", {
        method: "POST",
        body: {
          bank_id: Number(bankId),
          question_type: type,
          content,
          options: optionsText
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean),
          answer,
          score: Number(score),
          difficulty,
          knowledge_point: knowledge,
          knowledge_category: category,
        },
      }),
    onSuccess: () => {
      setContent("");
      setOptionsText("");
      setAnswer("");
      setKnowledge("");
      setCategory("");
      onCreated();
    },
    onError: (error) =>
      setNotice(`${text.createError}${error instanceof ApiError ? error.message : text.loadErrorHint}`),
  });

  const canSubmit = bankId && content.trim() && answer.trim() && Number(score) >= 1 && Number(score) <= 100;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={text.questionDialogTitle}
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
          <FormField id="q-bank" label={text.qBank}>
            <Select
              value={bankId}
              options={banks.map((bank) => ({ value: String(bank.id), label: bank.name }))}
              onChange={setBankId}
            />
          </FormField>
          <FormField id="q-type" label={text.qType}>
            <Select value={type} options={TYPE_OPTIONS} onChange={setType} />
          </FormField>
        </div>
        <FormField id="q-content" label={text.qContent}>
          <Textarea
            value={content}
            placeholder={text.qContentPlaceholder}
            onChange={(event) => setContent(event.target.value)}
          />
        </FormField>
        {type === "single_choice" || type === "multi_choice" ? (
          <FormField id="q-options" label={text.qOptions}>
            <Textarea
              value={optionsText}
              placeholder={text.qOptionsPlaceholder}
              onChange={(event) => setOptionsText(event.target.value)}
            />
          </FormField>
        ) : null}
        <FormField id="q-answer" label={text.qAnswer}>
          <Textarea
            value={answer}
            placeholder={text.qAnswerPlaceholder}
            onChange={(event) => setAnswer(event.target.value)}
          />
        </FormField>
        <div className={styles.row}>
          <FormField id="q-score" label={text.qScore}>
            <Input
              type="number"
              min="1"
              max="100"
              value={score}
              onChange={(event) => setScore(event.target.value)}
            />
          </FormField>
          <FormField id="q-difficulty" label={text.qDifficulty}>
            <Select value={difficulty} options={DIFFICULTY_OPTIONS} onChange={setDifficulty} />
          </FormField>
        </div>
        <div className={styles.row}>
          <FormField id="q-knowledge" label={text.qKnowledge}>
            <Input
              value={knowledge}
              placeholder={text.qKnowledgePlaceholder}
              onChange={(event) => setKnowledge(event.target.value)}
            />
          </FormField>
          <FormField id="q-category" label={text.qCategory}>
            <Input
              value={category}
              placeholder={text.qCategoryPlaceholder}
              onChange={(event) => setCategory(event.target.value)}
            />
          </FormField>
        </div>
        {notice ? <p className={styles.error}>{notice}</p> : null}
      </div>
    </Modal>
  );
}
