import { useEffect, useState } from "react";

import { Button } from "../../components/ui/button";
import { FormField } from "../../components/ui/form-field";
import { Input } from "../../components/ui/input";
import { Modal } from "../../components/ui/modal";
import { Select } from "../../components/ui/select";
import { Textarea } from "../../components/ui/textarea";
import { copy } from "../../content/copy";
import styles from "./dialogs.module.css";
import type { Course, Option } from "./types";

const text = copy.training;
const form = text.courseForm;

type Props = {
  open: boolean;
  course: Course | null;
  exams: Option[];
  busy: boolean;
  error: string;
  onClose: () => void;
  onSave: (payload: Record<string, unknown>) => void;
};

const DIFFICULTY = [
  { value: "easy", label: text.difficulty.easy },
  { value: "medium", label: text.difficulty.medium },
  { value: "hard", label: text.difficulty.hard },
];

export function CourseDialog({ open, course, exams, busy, error, onClose, onSave }: Props) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [duration, setDuration] = useState("2");
  const [difficulty, setDifficulty] = useState("medium");
  const [instructor, setInstructor] = useState("");
  const [examId, setExamId] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [nameError, setNameError] = useState("");

  useEffect(() => {
    if (!open) return;
    setName(course?.name ?? "");
    setCategory(course?.category ?? "");
    setDuration(String(course?.duration_hours ?? 2));
    setDifficulty(course?.difficulty ?? "medium");
    setInstructor(course?.instructor ?? "");
    setExamId(course?.exam_id ? String(course.exam_id) : "");
    setDescription(course?.description ?? "");
    setContent(course?.content ?? "");
    setNameError("");
  }, [open, course]);

  const examOptions = [{ value: "", label: text.courses.examNone }, ...exams.map((exam) => ({ value: String(exam.id), label: exam.name }))];

  function handleSubmit() {
    if (!name.trim()) {
      setNameError(form.nameRequired);
      return;
    }
    setNameError("");
    onSave({
      name: name.trim(),
      category: category.trim(),
      duration_hours: Number(duration) || 2,
      difficulty,
      instructor: instructor.trim(),
      exam_id: examId ? Number(examId) : null,
      description: description.trim(),
      content: content.trim(),
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={course ? form.editTitle : form.createTitle}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            {copy.common.cancel}
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={busy}>
            {form.save}
          </Button>
        </>
      }
    >
      <div className={styles.formGrid}>
        <FormField id="course-name" label={form.name} error={nameError}>
          <Input value={name} placeholder={form.namePlaceholder} onChange={(event) => setName(event.target.value)} />
        </FormField>
        <FormField id="course-category" label={form.category} hint={form.categoryHint}>
          <Input value={category} placeholder="算法 / 工程 / 产品" onChange={(event) => setCategory(event.target.value)} />
        </FormField>
        <FormField id="course-hours" label={form.duration}>
          <Input type="number" min={1} max={40} value={duration} onChange={(event) => setDuration(event.target.value)} />
        </FormField>
        <FormField id="course-difficulty" label={form.difficulty}>
          <Select id="course-difficulty" value={difficulty} options={DIFFICULTY} onChange={setDifficulty} ariaLabel={form.difficulty} />
        </FormField>
        <FormField id="course-instructor" label={form.instructor}>
          <Input value={instructor} onChange={(event) => setInstructor(event.target.value)} />
        </FormField>
        <FormField id="course-exam" label={form.exam}>
          <Select id="course-exam" value={examId} options={examOptions} onChange={setExamId} ariaLabel={form.exam} />
        </FormField>
        <FormField id="course-description" label={form.description} className={styles.full}>
          <Textarea rows={2} value={description} onChange={(event) => setDescription(event.target.value)} />
        </FormField>
        <FormField id="course-content" label={form.content} className={styles.full}>
          <Textarea rows={4} value={content} onChange={(event) => setContent(event.target.value)} />
        </FormField>
      </div>
      {error ? <p className={styles.formError} role="alert">{error}</p> : null}
    </Modal>
  );
}
