import { motion, AnimatePresence } from "framer-motion";
import { useLayoutEffect, useRef, useState } from "react";
import { useStageStore } from "@/state/useStageStore";
import { buildMissingBigSections } from "@/lib/recapMissingInfo";
import {
  DEGREE_LEVELS,
  FIELD_OF_STUDY_PRESETS,
  ROLE_PRESETS,
  SKILL_PRESETS,
} from "@/lib/profilePresets";
import { MonthRange, MonthYearPicker } from "../ui/MonthPicker";
import { formatMonthLabel, formatRange, isMonthRangeInvalid } from "../ui/monthPickerUtils";
import {
  ArrowRight,
  Sparkles,
  Plus,
  X,
  Code2,
  Database,
  Cloud,
  Wrench,
  Layers,
  Brain,
  Cpu,
  GitBranch,
  Boxes,
  Briefcase,
  GraduationCap,
  Award,
  FolderGit2,
  PencilLine,
  Target,
  Info,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

function visibleText(value: string | undefined): string {
  const cleaned = value?.trim() ?? "";
  return cleaned && cleaned !== "—" ? cleaned : "";
}

const SKILL_ICONS: Record<string, LucideIcon> = {
  default: Wrench,
  Python: Code2,
  Java: Cpu,
  PostgreSQL: Database,
  "RESTful APIs": GitBranch,
  Docker: Boxes,
  "AWS EC2": Cloud,
  Git: GitBranch,
  "Microservices Architecture": Layers,
  "Machine Learning": Brain,
};

export function RecapStage() {
  const setStage = useStageStore((s) => s.setStage);
  const identity = useStageStore((s) => s.identity);
  const setIdentityLead = useStageStore((s) => s.setIdentityLead);
  const identityLoading = useStageStore((s) => s.identityLoading);
  const skills = useStageStore((s) => s.skills);
  const interests = useStageStore((s) => s.interests);
  const addSkill = useStageStore((s) => s.addSkill);
  const removeSkill = useStageStore((s) => s.removeSkill);
  const addInterest = useStageStore((s) => s.addInterest);
  const removeInterest = useStageStore((s) => s.removeInterest);

  const experiences = useStageStore((s) => s.experiences);
  const addExperience = useStageStore((s) => s.addExperience);
  const removeExperience = useStageStore((s) => s.removeExperience);
  const educations = useStageStore((s) => s.educations);
  const addEducation = useStageStore((s) => s.addEducation);
  const removeEducation = useStageStore((s) => s.removeEducation);
  const certifications = useStageStore((s) => s.certifications);
  const addCertification = useStageStore((s) => s.addCertification);
  const removeCertification = useStageStore((s) => s.removeCertification);
  const projects = useStageStore((s) => s.projects);
  const addProject = useStageStore((s) => s.addProject);
  const removeProject = useStageStore((s) => s.removeProject);

  const [newSkill, setNewSkill] = useState("");
  const [newInterest, setNewInterest] = useState("");
  const leadTextareaRef = useRef<HTMLTextAreaElement>(null);

  const archetype = identity?.archetype ?? (identityLoading ? "…" : "professional");
  const lead =
    identity?.lead ??
    (identityLoading
      ? "Generating your career identity…"
      : "We mapped your profile to realistic next roles.");

  const missingBigSections = buildMissingBigSections({
    educations,
    experiences,
    skills,
    interests,
    certifications,
    projects,
  });

  useLayoutEffect(() => {
    const textarea = leadTextareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }, [lead]);

  return (
    <div className="relative w-full px-6 pb-6 pt-[max(5rem,calc(env(safe-area-inset-top)+4rem))] sm:px-10 lg:px-14 lg:pt-20">
      <PresetDatalist id="cc-skill-presets" options={SKILL_PRESETS} />
      <PresetDatalist id="cc-role-presets" options={ROLE_PRESETS} />
      <PresetDatalist id="cc-degree-presets" options={DEGREE_LEVELS} />
      <PresetDatalist id="cc-field-presets" options={FIELD_OF_STUDY_PRESETS} />
      <div className="mx-auto flex h-full w-full max-w-[1320px] flex-col gap-3">
        {/* Eyebrow — no name, no role line. */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.18em] text-foreground/65">
            <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--brand)]" />
            Analysis complete
          </span>
        </div>

        {/* Identity card — archetype + restored short lead text. */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="liquid-glass relative flex items-start gap-3 overflow-hidden rounded-2xl px-4 py-3"
        >
          <div
            className="grid h-11 w-11 shrink-0 place-items-center rounded-xl text-white"
            style={{ background: "var(--gradient-warm)" }}
          >
            <Sparkles size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-[color:var(--brand)]">
              Career identity
            </p>
            <p className="font-display text-[20px] leading-tight tracking-tight">
              You are a{" "}
              <span
                className="italic"
                style={{
                  background: "var(--gradient-warm)",
                  WebkitBackgroundClip: "text",
                  backgroundClip: "text",
                  color: "transparent",
                }}
              >
                {archetype}
              </span>
            </p>
            <div className="group relative mt-2">
              <textarea
                ref={leadTextareaRef}
                aria-label="Career context"
                value={lead}
                disabled={identityLoading && !identity}
                onChange={(e) => setIdentityLead(e.target.value)}
                className="block min-h-[4.5rem] w-full cursor-text resize-none overflow-hidden rounded-xl border border-foreground/10 bg-white/65 px-3 py-2 pr-9 text-[13.5px] leading-snug text-foreground/70 outline-none transition placeholder:text-foreground/35 hover:border-[color:var(--brand)]/25 focus:border-[color:var(--brand)]/35 focus:bg-white/80"
              />
              <PencilLine
                aria-hidden="true"
                size={14}
                className="pointer-events-none absolute right-3 top-2.5 text-foreground/35 transition group-hover:text-[color:var(--brand)] group-focus-within:text-[color:var(--brand)]"
              />
            </div>
          </div>
        </motion.div>

        {missingBigSections.length > 0 && <MissingInfoPrompt items={missingBigSections} />}

        {/* Consistent two-column rows across the recap. */}
        <div className="flex min-h-0 flex-1 flex-col gap-3">
          {/* Row 1 — Education (left) + Experience (right). */}
          <div className="grid gap-3 lg:grid-cols-2">
            <SectionCard icon={GraduationCap} title="Education" count={educations.length}>
              <div className="flex flex-col gap-1.5">
                <AnimatePresence initial={false}>
                  {educations.map((e, i) => (
                    <RowItem
                      key={`${e.school}-${i}`}
                      idx={i}
                      title={[e.degree, e.field].filter(Boolean).join(" — ") || "Education"}
                      subtitle={e.school}
                      meta={formatRange(e.start, e.end)}
                      onRemove={() => removeEducation(i)}
                    />
                  ))}
                </AnimatePresence>
                {educations.length === 0 && (
                  <EmptyPrompt>Add education history to improve matching.</EmptyPrompt>
                )}
                <AddEducationRow onAdd={(e) => addEducation(e)} />
              </div>
            </SectionCard>

            <SectionCard icon={Briefcase} title="Experience" count={experiences.length}>
              <div className="flex flex-col gap-1.5">
                <AnimatePresence initial={false}>
                  {experiences.map((e, i) => (
                    <RowItem
                      key={`${e.company}-${i}`}
                      idx={i}
                      title={e.role}
                      subtitle={e.company}
                      description={e.summary}
                      meta={formatRange(e.start, e.end)}
                      onRemove={() => removeExperience(i)}
                    />
                  ))}
                </AnimatePresence>
                {experiences.length === 0 && (
                  <EmptyPrompt>Add recent work or internship history.</EmptyPrompt>
                )}
                <AddExperienceRow onAdd={(e) => addExperience(e)} />
              </div>
            </SectionCard>
          </div>

          {/* Row 2 — Skills (left) + Interests (right). */}
          <div className="grid min-h-0 gap-3 lg:grid-cols-2">
            <SectionCard icon={Wrench} title="Skills" count={skills.length}>
              <div className="flex flex-1 flex-wrap content-start gap-1.5 overflow-y-auto">
                {skills.length === 0 && <EmptyPrompt>Add core technical skills.</EmptyPrompt>}
                <AnimatePresence initial={false}>
                  {skills.map((s, i) => {
                    const Icon = SKILL_ICONS[s.name] ?? SKILL_ICONS.default;
                    return (
                      <motion.div
                        key={s.name}
                        layout
                        initial={{ opacity: 0, scale: 0.85 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.85 }}
                        transition={{
                          delay: i * 0.02,
                          type: "spring",
                          stiffness: 400,
                          damping: 24,
                        }}
                        whileHover={{ y: -2 }}
                        className="group removable-chip removable-chip--white inline-flex max-w-full items-center gap-1.5 rounded-full border border-[color:var(--brand)]/15 bg-white/80 px-3 py-1.5 text-[13.5px] text-foreground/85"
                      >
                        <span
                          className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-white"
                          style={{ background: "var(--gradient-warm)" }}
                        >
                          <Icon size={11} />
                        </span>

                        <span className="removable-chip-label">{s.name}</span>
                        <button
                          type="button"
                          onClick={() => removeSkill(s.name)}
                          className="removable-chip-remove"
                          aria-label={`Remove ${s.name}`}
                        >
                          <X size={10} />
                        </button>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
                <AddPill
                  value={newSkill}
                  setValue={setNewSkill}
                  placeholder="Skill"
                  label="Add skill"
                  listId="cc-skill-presets"
                  onSubmit={() => {
                    addSkill(newSkill);
                    setNewSkill("");
                  }}
                />
              </div>
            </SectionCard>

            <SectionCard icon={Target} title="Interests" count={interests.length}>
              <div className="flex flex-1 flex-wrap content-start gap-1.5 overflow-y-auto">
                {interests.length === 0 && (
                  <EmptyPrompt icon={Target} title="No Interests Yet">
                    Add interests or target areas to improve recommendations.
                  </EmptyPrompt>
                )}
                <AnimatePresence initial={false}>
                  {interests.map((it, i) => (
                    <motion.div
                      key={it}
                      layout
                      initial={{ opacity: 0, scale: 0.85 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.85 }}
                      transition={{ delay: i * 0.02, type: "spring", stiffness: 400, damping: 24 }}
                      whileHover={{ y: -1 }}
                      className="group removable-chip removable-chip--brand inline-flex max-w-full items-center rounded-xl bg-[color:var(--brand)]/10 px-3 py-1.5 text-[13.5px] text-[color:var(--brand-deep)]"
                    >
                      <span className="removable-chip-label leading-snug">{it}</span>
                      <button
                        type="button"
                        onClick={() => removeInterest(it)}
                        className="removable-chip-remove"
                        aria-label={`Remove ${it}`}
                      >
                        <X size={10} />
                      </button>
                    </motion.div>
                  ))}
                </AnimatePresence>
                <AddPill
                  value={newInterest}
                  setValue={setNewInterest}
                  placeholder="Interest"
                  label="Add interest"
                  onSubmit={() => {
                    addInterest(newInterest);
                    setNewInterest("");
                  }}
                />
              </div>
            </SectionCard>
          </div>

          {/* Row 3 — Certifications (left) + Projects (right). */}
          <div className="grid min-h-0 gap-3 lg:grid-cols-2">
            <SectionCard icon={Award} title="Certifications" count={certifications.length}>
              <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto pr-1">
                <AnimatePresence initial={false}>
                  {certifications.map((c, i) => (
                    <RowItem
                      key={`${c.name}-${i}`}
                      idx={i}
                      icon={Award}
                      title={c.name}
                      subtitle={c.issuer}
                      meta={formatMonthLabel(c.year)}
                      onRemove={() => removeCertification(i)}
                    />
                  ))}
                </AnimatePresence>
                {certifications.length === 0 && (
                  <EmptyPrompt icon={Award} title="No Certifications Yet">
                    Add certifications if you have any.
                  </EmptyPrompt>
                )}
                <AddCertificationRow onAdd={(c) => addCertification(c)} />
              </div>
            </SectionCard>

            <SectionCard icon={FolderGit2} title="Projects" count={projects.length}>
              <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto pr-1">
                <AnimatePresence initial={false}>
                  {projects.map((p, i) => (
                    <RowItem
                      key={`${p.name}-${i}`}
                      idx={i}
                      icon={FolderGit2}
                      title={p.name}
                      subtitle={p.detail}
                      description={p.technologies.join(" · ")}
                      meta={formatRange(p.start, p.end)}
                      onRemove={() => removeProject(i)}
                    />
                  ))}
                </AnimatePresence>
                {projects.length === 0 && (
                  <EmptyPrompt icon={FolderGit2} title="No Projects Yet">
                    Add projects that show your skills.
                  </EmptyPrompt>
                )}
                <AddProjectRow onAdd={(p) => addProject(p)} />
              </div>
            </SectionCard>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          className="flex flex-wrap items-center justify-between gap-3"
        >
          <button
            onClick={() => setStage("entry")}
            className="text-[13px] text-foreground/60 transition hover:text-foreground"
          >
            ← back to input
          </button>
          <motion.button
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setStage("matching")}
            className="group inline-flex items-center gap-1.5 rounded-full px-5 py-2.5 text-[14px] font-medium text-white"
            style={{
              background: "var(--gradient-warm)",
              boxShadow:
                "0 10px 24px -12px color-mix(in oklab, var(--brand-deep) 60%, transparent)",
            }}
          >
            See matching roles
            <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
          </motion.button>
        </motion.div>
      </div>
    </div>
  );
}

/* ─────────────────────────  Building blocks  ───────────────────────── */

function PresetDatalist({ id, options }: { id: string; options: string[] }) {
  return (
    <datalist id={id}>
      {options.map((option) => (
        <option key={option} value={option} />
      ))}
    </datalist>
  );
}

function RowItem({
  idx,
  title,
  subtitle,
  description,
  meta,
  onRemove,
  icon: Icon,
}: {
  idx: number;
  title: string;
  subtitle?: string;
  description?: string;
  meta?: string;
  onRemove: () => void;
  icon?: LucideIcon;
}) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 6 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -6 }}
      transition={{ delay: idx * 0.03, type: "spring", stiffness: 340, damping: 26 }}
      className="group flex items-center gap-3 rounded-xl border border-foreground/10 bg-white/70 px-3 py-2"
    >
      {Icon ? (
        <Icon size={14} className="shrink-0 text-[color:var(--brand)]" />
      ) : (
        <span
          className="h-9 w-1 shrink-0 rounded-full"
          style={{ background: "var(--gradient-warm)" }}
        />
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-[14px] font-medium leading-tight">{title}</p>
        {visibleText(subtitle) && (
          <p className="truncate text-[12px] text-foreground/55">{subtitle}</p>
        )}
        {visibleText(description) && (
          <p className="line-clamp-2 text-[11.5px] leading-snug text-foreground/50">
            {description}
          </p>
        )}
      </div>
      {visibleText(meta) && (
        <span className="shrink-0 text-[12px] tabular-nums text-foreground/60">{meta}</span>
      )}
      <button onClick={onRemove} className="opacity-0 transition group-hover:opacity-100">
        <X size={12} className="text-foreground/50 hover:text-foreground" />
      </button>
    </motion.div>
  );
}

function AddPill({
  value,
  setValue,
  onSubmit,
  placeholder,
  label,
  listId,
}: {
  value: string;
  setValue: (v: string) => void;
  onSubmit: () => void;
  placeholder: string;
  label: string;
  listId?: string;
}) {
  const submit = () => {
    if (!value.trim()) return;
    onSubmit();
  };

  return (
    <div className="inline-flex max-w-full items-center gap-1 rounded-full border border-dashed border-foreground/20 bg-white/60 px-2 py-1 text-[13px]">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
        }}
        placeholder={placeholder}
        list={listId}
        className="w-24 min-w-0 bg-transparent py-0.5 outline-none placeholder:text-foreground/40"
      />
      <button
        type="button"
        onClick={submit}
        className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-white"
        style={{ background: "var(--gradient-warm)" }}
        aria-label={label}
      >
        <Plus size={11} />
      </button>
    </div>
  );
}

function SectionCard({
  icon: Icon,
  title,
  count,
  children,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  count?: number;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={cn("liquid-glass flex min-h-0 flex-col rounded-2xl p-4", className)}
    >
      <div className="mb-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={15} className="text-[color:var(--brand)]" />}
          <h3 className="font-display text-[16px] tracking-tight">{title}</h3>
        </div>
        {typeof count === "number" && (
          <span className="text-[12px] tabular-nums text-foreground/50">{count}</span>
        )}
      </div>

      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </motion.div>
  );
}

function EmptyPrompt({
  icon: Icon,
  title,
  children,
}: {
  icon?: LucideIcon;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex w-full items-start gap-2 rounded-xl border border-dashed border-foreground/15 bg-white/45 px-3 py-2 text-[12.5px] leading-snug text-foreground/50">
      {Icon && <Icon size={14} className="mt-0.5 shrink-0 text-[color:var(--brand)]" />}
      <div className="min-w-0">
        {title && <p className="font-medium text-foreground/65">{title}</p>}
        <p>{children}</p>
      </div>
    </div>
  );
}

function MissingInfoPrompt({ items }: { items: string[] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="liquid-glass flex items-start gap-2 rounded-2xl px-4 py-3 text-[13px] text-foreground/65"
    >
      <Info size={15} className="mt-0.5 shrink-0 text-[color:var(--brand)]" />
      <div className="min-w-0">
        <p className="font-medium text-foreground/80">
          Add missing info to improve recommendations.
        </p>
        <p className="mt-0.5">Missing: {items.join(", ")}. Add details in the sections below.</p>
      </div>
    </motion.div>
  );
}

/** Small footer shared by the richer add-rows: optional error + an Add button. */
function AddRowFooter({ error, onSubmit }: { error: string; onSubmit: () => void }) {
  return (
    <div className="flex items-center justify-between gap-2">
      {error ? (
        <p className="text-[11.5px] text-red-700" role="alert">
          {error}
        </p>
      ) : (
        <span />
      )}
      <button
        onClick={onSubmit}
        className="inline-flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-[12.5px] font-medium text-white"
        style={{ background: "var(--gradient-warm)" }}
      >
        <Plus size={12} />
        Add
      </button>
    </div>
  );
}

function AddExperienceRow({
  onAdd,
}: {
  onAdd: (e: {
    role: string;
    company: string;
    summary: string;
    start: string;
    end: string;
  }) => void;
}) {
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  const [summary, setSummary] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState("");
  const submit = () => {
    if (!role.trim() || !company.trim()) return;
    if (isMonthRangeInvalid(start, end)) {
      setError("End date can’t be before the start date.");
      return;
    }
    setError("");
    onAdd({
      role: role.trim(),
      company: company.trim(),
      summary: summary.trim(),
      start: start.trim(),
      end: end.trim() || "Present",
    });
    setRole("");
    setCompany("");
    setSummary("");
    setStart("");
    setEnd("");
  };
  return (
    <div className="mt-1 flex flex-col gap-2 rounded-lg border border-dashed border-foreground/15 bg-white/50 p-2">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <input
          value={role}
          onChange={(e) => setRole(e.target.value)}
          placeholder="Role"
          list="cc-role-presets"
          className="manual-input manual-input--sm"
        />
        <input
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder="Company"
          className="manual-input manual-input--sm"
        />
      </div>
      <input
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
        placeholder="Short description"
        className="manual-input manual-input--sm"
      />
      <MonthRange start={start} end={end} onStart={setStart} onEnd={setEnd} />
      <AddRowFooter error={error} onSubmit={submit} />
    </div>
  );
}

function AddEducationRow({
  onAdd,
}: {
  onAdd: (e: { degree: string; field: string; school: string; start: string; end: string }) => void;
}) {
  const [degree, setDegree] = useState("");
  const [field, setField] = useState("");
  const [school, setSchool] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState("");
  const submit = () => {
    if (!degree.trim() && !field.trim()) return;
    if (!school.trim()) return;
    if (isMonthRangeInvalid(start, end)) {
      setError("End date can’t be before the start date.");
      return;
    }
    setError("");
    onAdd({
      degree: degree.trim(),
      field: field.trim(),
      school: school.trim(),
      start: start.trim(),
      end: end.trim(),
    });
    setDegree("");
    setField("");
    setSchool("");
    setStart("");
    setEnd("");
  };
  return (
    <div className="mt-1 flex flex-col gap-2 rounded-lg border border-dashed border-foreground/15 bg-white/50 p-2">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <input
          value={degree}
          onChange={(e) => setDegree(e.target.value)}
          placeholder="Degree"
          list="cc-degree-presets"
          className="manual-input manual-input--sm"
        />
        <input
          value={field}
          onChange={(e) => setField(e.target.value)}
          placeholder="Field of study"
          list="cc-field-presets"
          className="manual-input manual-input--sm"
        />
      </div>
      <input
        value={school}
        onChange={(e) => setSchool(e.target.value)}
        placeholder="School"
        className="manual-input manual-input--sm"
      />
      <MonthRange start={start} end={end} onStart={setStart} onEnd={setEnd} />
      <AddRowFooter error={error} onSubmit={submit} />
    </div>
  );
}

function AddCertificationRow({
  onAdd,
}: {
  onAdd: (c: { name: string; issuer: string; year: string }) => void;
}) {
  const [name, setName] = useState("");
  const [issuer, setIssuer] = useState("");
  const [year, setYear] = useState("");
  const submit = () => {
    if (!name.trim()) return;
    onAdd({ name: name.trim(), issuer: issuer.trim(), year: year.trim() });
    setName("");
    setIssuer("");
    setYear("");
  };
  return (
    <div className="mt-1 flex flex-col gap-2 rounded-lg border border-dashed border-foreground/15 bg-white/50 p-2">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
          placeholder="Certification name"
          className="manual-input manual-input--sm"
        />
        <input
          value={issuer}
          onChange={(e) => setIssuer(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
          placeholder="Issuer"
          className="manual-input manual-input--sm"
        />
      </div>
      <MonthYearPicker value={year} onChange={setYear} placeholder="Issue date" compact />
      <AddRowFooter error="" onSubmit={submit} />
    </div>
  );
}

function AddProjectRow({
  onAdd,
}: {
  onAdd: (p: {
    name: string;
    detail: string;
    technologies: string[];
    start: string;
    end: string;
  }) => void;
}) {
  const [name, setName] = useState("");
  const [tech, setTech] = useState("");
  const [detail, setDetail] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState("");
  const submit = () => {
    if (!name.trim()) return;
    if (isMonthRangeInvalid(start, end)) {
      setError("End date can’t be before the start date.");
      return;
    }
    setError("");
    onAdd({
      name: name.trim(),
      detail: detail.trim(),
      technologies: tech
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      start: start.trim(),
      end: end.trim(),
    });
    setName("");
    setTech("");
    setDetail("");
    setStart("");
    setEnd("");
  };
  return (
    <div className="mt-1 flex flex-col gap-2 rounded-lg border border-dashed border-foreground/15 bg-white/50 p-2">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Project name"
          className="manual-input manual-input--sm"
        />
        <input
          value={tech}
          onChange={(e) => setTech(e.target.value)}
          placeholder="Technologies, comma-separated"
          className="manual-input manual-input--sm"
        />
      </div>
      <input
        value={detail}
        onChange={(e) => setDetail(e.target.value)}
        placeholder="Short description"
        className="manual-input manual-input--sm"
      />
      <MonthRange start={start} end={end} onStart={setStart} onEnd={setEnd} />
      <AddRowFooter error={error} onSubmit={submit} />
    </div>
  );
}
