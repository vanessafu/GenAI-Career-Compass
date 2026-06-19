import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useStageStore } from "@/state/useStageStore";
import { cn } from "@/lib/utils";
import { Upload, FileText, X, Plus, ArrowRight, Sparkles, ChevronDown } from "lucide-react";
import { LoadingPanel } from "../ui/LoadingPanel";

const PARSE_STEPS = ["Reading your profile", "Extracting skills", "Mapping roles"];
const MANUAL_STEPS = ["Structuring your profile", "Mapping skills", "Mapping roles"];

const SENIORITY_OPTIONS = ["Student", "Junior", "Mid", "Senior", "Lead"];

const ROLE_PRESETS = [
  "Senior Backend Developer",
  "Backend Developer",
  "Full-Stack Engineer",
  "Frontend Engineer",
  "DevOps Engineer",
  "Tech Lead",
  "Engineering Manager",
  "Data Engineer",
  "Cloud Engineer",
  "Product Designer",
];

const EDU_PRESETS = [
  "MSc Computer Science",
  "BSc Computer Science",
  "BSc Information Systems",
  "MSc Information Systems",
  "MSc Data Science",
  "Self-taught",
  "Bootcamp",
  "PhD Computer Science",
];

const SKILL_PRESETS = [
  "Python",
  "Java",
  "PostgreSQL",
  "RESTful APIs",
  "Docker",
  "AWS EC2",
  "Git",
  "Microservices Architecture",
  "TypeScript",
  "React",
  "Node.js",
  "Go",
  "Kubernetes",
  "GraphQL",
  "Redis",
  "System Design",
  "Mentoring",
];

export function EntryStage() {
  const setStage = useStageStore((s) => s.setStage);
  const uploadCv = useStageStore((s) => s.uploadCv);
  const submitManualProfile = useStageStore((s) => s.submitManualProfile);

  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const fileName = file?.name ?? null;

  // Tier 1 — quick start
  const [role, setRole] = useState("");
  const [seniority, setSeniority] = useState("");
  const [yearsOfExperience, setYearsOfExperience] = useState("");
  const [degree, setDegree] = useState("");
  const [school, setSchool] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [skillDraft, setSkillDraft] = useState("");
  const [interests, setInterests] = useState("");

  // Tier 2 — add more context (collapsed by default)
  const [showMore, setShowMore] = useState(false);
  const [latestJobRole, setLatestJobRole] = useState("");
  const [latestJobCompany, setLatestJobCompany] = useState("");
  const [latestJobFrom, setLatestJobFrom] = useState("");
  const [latestJobTo, setLatestJobTo] = useState("");
  const [summary, setSummary] = useState("");
  const [softSkills, setSoftSkills] = useState<string[]>([]);
  const [softSkillDraft, setSoftSkillDraft] = useState("");
  const [languageName, setLanguageName] = useState("");
  const [languageLevel, setLanguageLevel] = useState("");

  const [parsing, setParsing] = useState(false);
  const [steps, setSteps] = useState<string[]>(PARSE_STEPS);
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    const timers = timersRef.current;
    return () => timers.forEach(clearTimeout);
  }, []);

  const addSkill = (s: string) => {
    const val = s.trim();
    if (!val || skills.includes(val)) return;
    setSkills([...skills, val]);
    setSkillDraft("");
  };

  const addSoftSkill = (s: string) => {
    const val = s.trim();
    if (!val || softSkills.includes(val)) return;
    setSoftSkills([...softSkills, val]);
    setSoftSkillDraft("");
  };

  const analyzeCv = async () => {
    if (parsing) return;
    if (!file) {
      setFormError("Please choose a PDF file first.");
      return;
    }
    setFormError(null);
    setSteps(PARSE_STEPS);
    setParsing(true);
    setStep(0);
    setDone(false);
    timersRef.current.push(setTimeout(() => setStep(1), 700));
    timersRef.current.push(setTimeout(() => setStep(2), 1400));

    const ok = await uploadCv(file);
    if (ok) {
      setDone(true);
      timersRef.current.push(setTimeout(() => setStage("recap"), 600));
    } else {
      setParsing(false);
      setFormError(useStageStore.getState().error);
    }
  };

  const buildManualProfile = async () => {
    if (parsing) return;
    if (!role.trim() && skills.length === 0) {
      setFormError("Add at least your current role or one skill.");
      return;
    }
    setFormError(null);
    setSteps(MANUAL_STEPS);
    setParsing(true);
    setStep(0);
    setDone(false);
    timersRef.current.push(setTimeout(() => setStep(1), 500));
    timersRef.current.push(setTimeout(() => setStep(2), 1000));

    const ok = await submitManualProfile({
      currentRole: role,
      seniority,
      yearsOfExperience,
      degree,
      school,
      skills,
      interests,
      latestJobRole,
      latestJobCompany,
      latestJobFrom,
      latestJobTo,
      summary,
      softSkills,
      languageName,
      languageLevel,
    });
    if (ok) {
      setDone(true);
      timersRef.current.push(setTimeout(() => setStage("recap"), 600));
    } else {
      setParsing(false);
      setFormError(useStageStore.getState().error);
    }
  };

  return (
    <div className="relative flex w-full flex-col items-stretch px-6 pb-10 pt-[max(6rem,calc(env(safe-area-inset-top)+5rem))] sm:px-10 lg:h-full lg:justify-center lg:px-16 lg:pt-24">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-7">
        {/* Headline — transform-only animation, glides centered when loading appears. */}
        <motion.div
          animate={{ scale: parsing ? 0.86 : 1, y: parsing ? 4 : 0 }}
          transition={{ type: "spring", stiffness: 180, damping: 30, mass: 0.9 }}
          style={{ transformOrigin: parsing ? "center top" : "left top", willChange: "transform" }}
          className={cn(
            "flex flex-col transition-[align-items,text-align] duration-500",
            parsing ? "items-center text-center" : "items-start max-w-2xl",
          )}
        >
          <h1 className="h-hero">
            Map your expertise to{" "}
            <span
              className="italic"
              style={{
                background: "var(--gradient-warm)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              future opportunities.
            </span>
          </h1>
          <motion.p
            animate={{
              opacity: parsing ? 0 : 1,
              height: parsing ? 0 : "auto",
              marginTop: parsing ? 0 : 12,
            }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
            className="max-w-[58ch] overflow-hidden text-[15px] leading-relaxed text-foreground/65"
          >
            Upload your CV or fill in a short profile. We map your strengths to realistic next
            roles.
          </motion.p>
        </motion.div>

        {formError && !parsing && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-auto w-full max-w-xl rounded-2xl border border-red-300/60 bg-red-50/80 px-4 py-3 text-[13px] text-red-700"
            role="alert"
          >
            {formError}
          </motion.div>
        )}

        <AnimatePresence mode="popLayout" initial={false}>
          {parsing ? (
            <LoadingPanel
              key="parsing"
              icon={FileText}
              title="Building your profile"
              doneTitle="Profile ready"
              step={step}
              steps={steps}
              done={done}
            />
          ) : (
            <motion.div
              key="cards"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              className="grid w-full gap-5 md:grid-cols-2"
            >
              {/* ── Upload CV ── */}
              <motion.div
                whileHover={{ y: -3 }}
                transition={{ type: "spring", stiffness: 260, damping: 22 }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDrag(true);
                }}
                onDragLeave={() => setDrag(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDrag(false);
                  const f = e.dataTransfer.files?.[0];
                  if (f) {
                    setFile(f);
                    setFormError(null);
                  }
                }}
                className={cn(
                  "liquid-glass flex flex-col rounded-3xl p-6 transition-colors",
                  drag && "ring-2 ring-[color:var(--brand)]/50",
                )}
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-[22px] tracking-tight">Upload your CV</h3>
                  <span
                    className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10.5px] font-medium text-white"
                    style={{ background: "var(--gradient-warm)" }}
                  >
                    <Sparkles size={11} /> AI parsing
                  </span>
                </div>
                <p className="mt-1 text-[13.5px] text-foreground/60">
                  We extract role, skills and interests automatically.
                </p>

                <motion.div
                  animate={drag ? { scale: 1.01 } : { scale: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  className={cn(
                    "mt-4 flex flex-1 flex-col items-center justify-center gap-3 rounded-2xl border border-dashed p-6 text-center transition-colors",
                    drag
                      ? "border-[color:var(--brand)]/60 bg-[color:var(--brand)]/[0.06]"
                      : "border-foreground/15 bg-white/55",
                  )}
                >
                  <motion.div
                    animate={drag ? { y: -2 } : { y: 0 }}
                    className="grid h-14 w-14 place-items-center rounded-2xl text-white"
                    style={{ background: "var(--gradient-warm)" }}
                  >
                    <Upload size={20} />
                  </motion.div>
                  <p className="text-[14.5px] font-medium">
                    {fileName ?? "Drag & drop, or click to browse"}
                  </p>
                  <label className="liquid-glass inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-full px-3.5 py-1.5 text-[12.5px] text-foreground/80 transition hover:text-foreground">
                    <input
                      type="file"
                      accept="application/pdf,.pdf"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) {
                          setFile(f);
                          setFormError(null);
                        }
                      }}
                    />
                    Browse files
                  </label>
                </motion.div>

                <motion.button
                  whileHover={{ y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={analyzeCv}
                  className="group mt-5 inline-flex items-center justify-center gap-1.5 rounded-full px-5 py-2.5 text-[14px] font-medium text-white"
                  style={{
                    background: "var(--gradient-warm)",
                    boxShadow:
                      "0 10px 24px -12px color-mix(in oklab, var(--brand-deep) 60%, transparent)",
                  }}
                >
                  Analyze my CV
                  <ArrowRight
                    size={14}
                    className="transition-transform group-hover:translate-x-0.5"
                  />
                </motion.button>
              </motion.div>

              {/* ── Manual entry ── */}
              <motion.div
                transition={{ type: "spring", stiffness: 260, damping: 22 }}
                className="liquid-glass flex flex-col gap-3.5 rounded-3xl p-6 lg:max-h-[78vh] lg:overflow-y-auto"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-[22px] tracking-tight">Fill it in manually</h3>
                  <span className="rounded-full bg-[color:var(--brand)]/10 px-2 py-0.5 text-[10.5px] font-medium text-[color:var(--brand)]">
                    Quick form
                  </span>
                </div>

                <div className="grid gap-2.5 sm:grid-cols-2">
                  <AutocompleteInput
                    label="Current role"
                    value={role}
                    onChange={setRole}
                    presets={ROLE_PRESETS}
                    placeholder="e.g. Senior Backend Developer"
                  />
                  <label className="block">
                    <span className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                      Seniority
                    </span>
                    <select
                      value={seniority}
                      onChange={(e) => setSeniority(e.target.value)}
                      className="manual-input"
                    >
                      <option value="">Select…</option>
                      {SENIORITY_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="grid gap-2.5 sm:grid-cols-2">
                  <AutocompleteInput
                    label="Degree"
                    value={degree}
                    onChange={setDegree}
                    presets={EDU_PRESETS}
                    placeholder="e.g. MSc Computer Science"
                  />
                  <label className="block">
                    <span className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                      School
                    </span>
                    <input
                      value={school}
                      onChange={(e) => setSchool(e.target.value)}
                      placeholder="e.g. TU Munich"
                      className="manual-input"
                    />
                  </label>
                </div>

                <label className="block sm:w-1/2 sm:pr-1.5">
                  <span className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                    Years of experience
                  </span>
                  <input
                    type="number"
                    min={0}
                    max={80}
                    value={yearsOfExperience}
                    onChange={(e) => setYearsOfExperience(e.target.value)}
                    placeholder="e.g. 5"
                    className="manual-input"
                  />
                </label>

                <div>
                  <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                    Technical skills
                  </p>
                  <TagField
                    tags={skills}
                    onRemove={(t) => setSkills(skills.filter((x) => x !== t))}
                    typeahead={
                      <SkillTypeahead
                        draft={skillDraft}
                        setDraft={setSkillDraft}
                        onAdd={addSkill}
                        existing={skills}
                      />
                    }
                  />
                </div>

                <div>
                  <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                    What are you drawn to?
                  </p>
                  <textarea
                    value={interests}
                    onChange={(e) => setInterests(e.target.value)}
                    rows={2}
                    maxLength={200}
                    placeholder="e.g. AI, open source, automation…"
                    className="manual-input resize-none"
                  />
                </div>

                {/* Collapsible Tier 2 — add more context */}
                <button
                  type="button"
                  onClick={() => setShowMore((v) => !v)}
                  className="inline-flex w-fit items-center gap-1.5 text-[12.5px] font-medium text-[color:var(--brand-deep)] transition hover:opacity-80"
                >
                  <ChevronDown
                    size={14}
                    className={cn("transition-transform", showMore && "rotate-180")}
                  />
                  {showMore ? "Hide extra details" : "Add more context (optional)"}
                </button>

                <AnimatePresence initial={false}>
                  {showMore && (
                    <motion.div
                      key="more"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                      className="overflow-hidden"
                    >
                      <div className="flex flex-col gap-3.5 pt-0.5">
                        <div>
                          <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                            Most recent job
                          </p>
                          <div className="grid gap-2.5 sm:grid-cols-2">
                            <input
                              value={latestJobRole}
                              onChange={(e) => setLatestJobRole(e.target.value)}
                              placeholder="Role"
                              className="manual-input"
                            />
                            <input
                              value={latestJobCompany}
                              onChange={(e) => setLatestJobCompany(e.target.value)}
                              placeholder="Company"
                              className="manual-input"
                            />
                            <input
                              value={latestJobFrom}
                              onChange={(e) => setLatestJobFrom(e.target.value)}
                              placeholder="From (e.g. 2021)"
                              className="manual-input"
                            />
                            <input
                              value={latestJobTo}
                              onChange={(e) => setLatestJobTo(e.target.value)}
                              placeholder="To (e.g. Present)"
                              className="manual-input"
                            />
                          </div>
                        </div>

                        <div>
                          <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                            Professional summary
                          </p>
                          <textarea
                            value={summary}
                            onChange={(e) => setSummary(e.target.value)}
                            rows={2}
                            maxLength={300}
                            placeholder="A sentence or two about your focus and strengths…"
                            className="manual-input resize-none"
                          />
                        </div>

                        <div>
                          <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                            Soft skills
                          </p>
                          <TagField
                            tags={softSkills}
                            onRemove={(t) => setSoftSkills(softSkills.filter((x) => x !== t))}
                            typeahead={
                              <PlainTagInput
                                draft={softSkillDraft}
                                setDraft={setSoftSkillDraft}
                                onAdd={addSoftSkill}
                                placeholder="Add soft skill"
                              />
                            }
                          />
                        </div>

                        <div>
                          <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                            Language
                          </p>
                          <div className="grid gap-2.5 sm:grid-cols-2">
                            <input
                              value={languageName}
                              onChange={(e) => setLanguageName(e.target.value)}
                              placeholder="e.g. English"
                              className="manual-input"
                            />
                            <input
                              value={languageLevel}
                              onChange={(e) => setLanguageLevel(e.target.value)}
                              placeholder="e.g. C2 / Native"
                              className="manual-input"
                            />
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <p className="text-[11.5px] leading-snug text-foreground/50">
                  You can add more experience, projects and certifications on the next screen.
                </p>

                <motion.button
                  whileHover={{ y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={buildManualProfile}
                  className="group mt-1 inline-flex items-center justify-center gap-1.5 rounded-full px-5 py-2.5 text-[14px] font-medium text-white"
                  style={{
                    background: "var(--gradient-warm)",
                    boxShadow:
                      "0 10px 24px -12px color-mix(in oklab, var(--brand-deep) 60%, transparent)",
                  }}
                >
                  Build my profile
                  <ArrowRight
                    size={14}
                    className="transition-transform group-hover:translate-x-0.5"
                  />
                </motion.button>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <style>{`
        .manual-input {
          width: 100%;
          border: 1px solid color-mix(in oklab, currentColor 10%, transparent);
          background: rgba(255,255,255,0.7);
          border-radius: 0.75rem;
          padding: 0.6rem 0.8rem;
          font-size: 13.5px;
          color: var(--foreground);
          outline: none;
          transition: border-color .15s, box-shadow .15s;
        }
        .manual-input::placeholder { color: color-mix(in oklab, currentColor 40%, transparent); }
        .manual-input:focus {
          border-color: color-mix(in oklab, var(--brand) 55%, transparent);
          box-shadow: 0 0 0 3px color-mix(in oklab, var(--brand) 14%, transparent);
        }
      `}</style>
    </div>
  );
}

/* ─────────────────────────  Autocomplete inputs  ───────────────────────── */

function AutocompleteInput({
  label,
  value,
  onChange,
  presets,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  presets: string[];
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const matches = presets
    .filter((p) => p.toLowerCase().includes(value.toLowerCase()) && p !== value)
    .slice(0, 6);
  return (
    <label className="relative block">
      <span className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
        {label}
      </span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        className="manual-input"
      />
      <AnimatePresence>
        {open && matches.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute left-0 right-0 top-full z-30 mt-1 max-h-44 overflow-y-auto rounded-xl border border-foreground/10 bg-white/95 p-1.5 shadow-lg backdrop-blur"
          >
            {matches.map((m) => (
              <button
                key={m}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onChange(m);
                  setOpen(false);
                }}
                className="block w-full rounded-md px-2 py-1.5 text-left text-[12.5px] text-foreground/80 hover:bg-foreground/5"
              >
                {m}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </label>
  );
}

function SkillTypeahead({
  draft,
  setDraft,
  onAdd,
  existing,
}: {
  draft: string;
  setDraft: (v: string) => void;
  onAdd: (v: string) => void;
  existing: string[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative flex min-w-[120px] flex-1 items-center gap-1">
      <Plus size={12} className="text-foreground/40" />
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            onAdd(draft);
          }
        }}
        placeholder="Add skill"
        className="w-full bg-transparent py-1 text-[13px] outline-none placeholder:text-foreground/40"
      />
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute left-0 right-0 top-full z-20 mt-1 max-h-44 overflow-y-auto rounded-xl border border-foreground/10 bg-white/95 p-1.5 shadow-lg backdrop-blur"
          >
            {SKILL_PRESETS.filter(
              (p) => !existing.includes(p) && p.toLowerCase().includes(draft.toLowerCase()),
            )
              .slice(0, 8)
              .map((p) => (
                <button
                  key={p}
                  onMouseDown={() => onAdd(p)}
                  className="block w-full rounded-md px-2 py-1.5 text-left text-[12.5px] text-foreground/80 hover:bg-foreground/5"
                >
                  {p}
                </button>
              ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Tag chips container with a trailing input slot (typeahead or plain). */
function TagField({
  tags,
  onRemove,
  typeahead,
}: {
  tags: string[];
  onRemove: (tag: string) => void;
  typeahead: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-foreground/10 bg-white/65 px-2 py-2">
      <AnimatePresence initial={false}>
        {tags.map((t) => (
          <motion.span
            key={t}
            layout
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.6, opacity: 0 }}
            transition={{ type: "spring", stiffness: 380, damping: 22 }}
            className="inline-flex items-center gap-1 rounded-full bg-[color:var(--brand)]/10 px-2.5 py-0.5 text-[12px] text-[color:var(--brand)]"
          >
            {t}
            <button
              onClick={() => onRemove(t)}
              className="opacity-60 hover:opacity-100"
              aria-label={`remove ${t}`}
            >
              <X size={11} />
            </button>
          </motion.span>
        ))}
      </AnimatePresence>
      {typeahead}
    </div>
  );
}

/** Free-text tag input (no preset list), used for soft skills. */
function PlainTagInput({
  draft,
  setDraft,
  onAdd,
  placeholder,
}: {
  draft: string;
  setDraft: (v: string) => void;
  onAdd: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="flex min-w-[120px] flex-1 items-center gap-1">
      <Plus size={12} className="text-foreground/40" />
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            onAdd(draft);
          }
        }}
        placeholder={placeholder}
        className="w-full bg-transparent py-1 text-[13px] outline-none placeholder:text-foreground/40"
      />
    </div>
  );
}
