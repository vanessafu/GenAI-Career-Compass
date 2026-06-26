import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useStageStore } from "@/state/useStageStore";
import { cn } from "@/lib/utils";
import {
  CV_UPLOAD_PROGRESS,
  MANUAL_PROFILE_PROGRESS,
  getLoadingProgressState,
  type LoadingProgressConfig,
} from "@/lib/loadingProgress";
import { Upload, FileText, X, Plus, ArrowRight, Sparkles, ChevronDown } from "lucide-react";
import { LoadingPanel } from "../ui/LoadingPanel";

const PARSE_STEPS = ["Reading your CV", "Privacy-stripping data", "Generating identity"];
const MANUAL_STEPS = ["Structuring your profile", "Privacy-stripping data", "Generating identity"];

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
  const [education, setEducation] = useState<
    {
      degree: string;
      institution: string;
      fieldOfStudy: string;
      startDate: string;
      endDate: string;
    }[]
  >([]);
  const [experience, setExperience] = useState<
    { role: string; organization: string; startDate: string; endDate: string }[]
  >([]);
  const [educationDraft, setEducationDraft] = useState({
    degree: "",
    institution: "",
    fieldOfStudy: "",
    startDate: "",
    endDate: "",
  });
  const [experienceDraft, setExperienceDraft] = useState({
    role: "",
    organization: "",
    startDate: "",
    endDate: "",
  });
  const [seniority, setSeniority] = useState("");
  const [yearsOfExperience, setYearsOfExperience] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [skillDraft, setSkillDraft] = useState("");
  const [interests, setInterests] = useState<string[]>([]);
  const [interestDraft, setInterestDraft] = useState("");
  const [targetConstraints, setTargetConstraints] = useState<string[]>([]);
  const [targetConstraintDraft, setTargetConstraintDraft] = useState("");

  // Tier 2 — add more context (collapsed by default)
  const [showMore, setShowMore] = useState(false);
  const [summary, setSummary] = useState("");
  const [softSkills, setSoftSkills] = useState<string[]>([]);
  const [softSkillDraft, setSoftSkillDraft] = useState("");
  const [languageName, setLanguageName] = useState("");
  const [languageLevel, setLanguageLevel] = useState("");
  const [projects, setProjects] = useState<
    {
      title: string;
      description: string;
      technologies: string[];
      startDate: string;
      endDate: string;
    }[]
  >([]);
  const [projectDraft, setProjectDraft] = useState({
    title: "",
    description: "",
    technologies: "",
    startDate: "",
    endDate: "",
  });
  const [certifications, setCertifications] = useState<
    { name: string; issuingOrganization: string; issueDate: string }[]
  >([]);
  const [certificationDraft, setCertificationDraft] = useState({
    name: "",
    issuingOrganization: "",
    issueDate: "",
  });

  const [parsing, setParsing] = useState(false);
  const [steps, setSteps] = useState<string[]>(PARSE_STEPS);
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(8);
  const [done, setDone] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach(clearTimeout);
      if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    };
  }, []);

  const clearLoadingTimers = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  };

  const startProgress = (config: LoadingProgressConfig) => {
    clearLoadingTimers();
    const startedAt = Date.now();
    const tick = () => {
      const state = getLoadingProgressState(config, Date.now() - startedAt);
      setStep(state.step);
      setProgress(state.progress);
    };

    tick();
    progressTimerRef.current = setInterval(tick, 250);
  };

  const finishProgress = () => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    setProgress(100);
    setDone(true);
  };

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

  const addInterest = (s: string) => {
    const val = s.trim();
    if (!val || interests.some((item) => item.toLowerCase() === val.toLowerCase())) return;
    setInterests([...interests, val]);
    setInterestDraft("");
  };

  const addTargetConstraint = (s: string) => {
    const val = s.trim();
    if (!val || targetConstraints.some((item) => item.toLowerCase() === val.toLowerCase())) return;
    setTargetConstraints([...targetConstraints, val]);
    setTargetConstraintDraft("");
  };

  const addEducation = () => {
    if (!educationDraft.degree.trim()) return;
    setEducation([
      ...education,
      {
        degree: educationDraft.degree.trim(),
        institution: educationDraft.institution.trim(),
        fieldOfStudy: educationDraft.fieldOfStudy.trim(),
        startDate: educationDraft.startDate.trim(),
        endDate: educationDraft.endDate.trim(),
      },
    ]);
    setEducationDraft({
      degree: "",
      institution: "",
      fieldOfStudy: "",
      startDate: "",
      endDate: "",
    });
  };

  const addExperience = () => {
    if (!experienceDraft.role.trim()) return;
    setExperience([
      ...experience,
      {
        role: experienceDraft.role.trim(),
        organization: experienceDraft.organization.trim(),
        startDate: experienceDraft.startDate.trim(),
        endDate: experienceDraft.endDate.trim(),
      },
    ]);
    setExperienceDraft({ role: "", organization: "", startDate: "", endDate: "" });
  };

  const addProject = () => {
    if (!projectDraft.title.trim()) return;
    setProjects([
      ...projects,
      {
        title: projectDraft.title.trim(),
        description: projectDraft.description.trim(),
        technologies: projectDraft.technologies
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        startDate: projectDraft.startDate.trim(),
        endDate: projectDraft.endDate.trim(),
      },
    ]);
    setProjectDraft({ title: "", description: "", technologies: "", startDate: "", endDate: "" });
  };

  const addCertification = () => {
    if (!certificationDraft.name.trim()) return;
    setCertifications([
      ...certifications,
      {
        name: certificationDraft.name.trim(),
        issuingOrganization: certificationDraft.issuingOrganization.trim(),
        issueDate: certificationDraft.issueDate.trim(),
      },
    ]);
    setCertificationDraft({ name: "", issuingOrganization: "", issueDate: "" });
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
    setDone(false);
    startProgress(CV_UPLOAD_PROGRESS);

    const ok = await uploadCv(file);
    if (ok) {
      finishProgress();
      timersRef.current.push(setTimeout(() => setStage("recap"), 600));
    } else {
      clearLoadingTimers();
      setParsing(false);
      setFormError(useStageStore.getState().error);
    }
  };

  const buildManualProfile = async () => {
    if (parsing) return;
    const parsedYears = yearsOfExperience.trim() === "" ? null : Number(yearsOfExperience);
    if (!role.trim()) {
      setFormError("Add your current role.");
      return;
    }
    if (!seniority.trim()) {
      setFormError("Select your seniority.");
      return;
    }
    if (
      parsedYears === null ||
      !Number.isInteger(parsedYears) ||
      parsedYears < 0 ||
      parsedYears > 80
    ) {
      setFormError("Add years of experience as a whole number from 0 to 80.");
      return;
    }
    if (skills.length === 0) {
      setFormError("Add at least one technical skill.");
      return;
    }
    if (interests.length === 0 && targetConstraints.length === 0) {
      setFormError("Add at least one interest or target constraint.");
      return;
    }
    setFormError(null);
    setSteps(MANUAL_STEPS);
    setParsing(true);
    setDone(false);
    startProgress(MANUAL_PROFILE_PROGRESS);

    const ok = await submitManualProfile({
      currentRole: role,
      seniorityLevel: seniority,
      yearsOfExperience: parsedYears,
      education,
      experience,
      skills,
      interests,
      targetConstraints,
      summary,
      softSkills,
      languageName,
      languageLevel,
      projects,
      certifications,
    });
    if (ok) {
      finishProgress();
      timersRef.current.push(setTimeout(() => setStage("recap"), 600));
    } else {
      clearLoadingTimers();
      setParsing(false);
      setFormError(useStageStore.getState().error);
    }
  };

  return (
    <div className="relative flex w-full flex-col items-stretch px-6 pb-10 pt-[max(4.75rem,calc(env(safe-area-inset-top)+4.25rem))] sm:px-10 sm:pt-20 lg:px-16 lg:pt-[5.5rem]">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-5 sm:gap-6">
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
            Mapping your expertise to{" "}
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
              progress={progress}
            />
          ) : (
            <motion.div
              key="cards"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              className="grid w-full items-start gap-5 md:grid-cols-2"
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
                className="liquid-glass flex flex-col gap-3.5 rounded-3xl p-6"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-[22px] tracking-tight">Fill it in manually</h3>
                  <span className="rounded-full bg-[color:var(--brand)]/10 px-2 py-0.5 text-[10.5px] font-medium text-[color:var(--brand)]">
                    Quick form
                  </span>
                </div>

                <div className="grid gap-2.5">
                  <AutocompleteInput
                    label="Current role"
                    value={role}
                    onChange={setRole}
                    presets={ROLE_PRESETS}
                    placeholder="e.g. Senior Backend Developer"
                  />
                  <div className="grid gap-2.5 sm:grid-cols-2">
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
                    <label className="block">
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
                  </div>
                </div>

                <RepeatableSection
                  title="Education"
                  items={education.map((item) => ({
                    title: item.degree,
                    subtitle: [item.fieldOfStudy, item.institution].filter(Boolean).join(" · "),
                    meta: [item.startDate, item.endDate].filter(Boolean).join("-"),
                  }))}
                  onRemove={(idx) => setEducation(education.filter((_, i) => i !== idx))}
                >
                  <div className="grid gap-2.5 sm:grid-cols-2">
                    <AutocompleteInput
                      label="Degree"
                      value={educationDraft.degree}
                      onChange={(value) => setEducationDraft({ ...educationDraft, degree: value })}
                      presets={EDU_PRESETS}
                      placeholder="e.g. MSc Robotics"
                    />
                    <input
                      value={educationDraft.institution}
                      onChange={(e) =>
                        setEducationDraft({ ...educationDraft, institution: e.target.value })
                      }
                      placeholder="Institution"
                      className="manual-input self-end"
                    />
                    <input
                      value={educationDraft.fieldOfStudy}
                      onChange={(e) =>
                        setEducationDraft({ ...educationDraft, fieldOfStudy: e.target.value })
                      }
                      placeholder="Field of study"
                      className="manual-input"
                    />
                    <div className="grid grid-cols-2 gap-2.5">
                      <input
                        value={educationDraft.startDate}
                        onChange={(e) =>
                          setEducationDraft({ ...educationDraft, startDate: e.target.value })
                        }
                        placeholder="From"
                        className="manual-input"
                      />
                      <input
                        value={educationDraft.endDate}
                        onChange={(e) =>
                          setEducationDraft({ ...educationDraft, endDate: e.target.value })
                        }
                        placeholder="To"
                        className="manual-input"
                      />
                    </div>
                  </div>
                  <AddRowButton onClick={addEducation} label="Add education" />
                </RepeatableSection>

                <RepeatableSection
                  title="Experience"
                  items={experience.map((item) => ({
                    title: item.role,
                    subtitle: item.organization,
                    meta: [item.startDate, item.endDate || "Present"].filter(Boolean).join("-"),
                  }))}
                  onRemove={(idx) => setExperience(experience.filter((_, i) => i !== idx))}
                >
                  <div className="grid gap-2.5 sm:grid-cols-2">
                    <input
                      value={experienceDraft.role}
                      onChange={(e) =>
                        setExperienceDraft({ ...experienceDraft, role: e.target.value })
                      }
                      placeholder="Role"
                      className="manual-input"
                    />
                    <input
                      value={experienceDraft.organization}
                      onChange={(e) =>
                        setExperienceDraft({ ...experienceDraft, organization: e.target.value })
                      }
                      placeholder="Organization"
                      className="manual-input"
                    />
                    <input
                      value={experienceDraft.startDate}
                      onChange={(e) =>
                        setExperienceDraft({ ...experienceDraft, startDate: e.target.value })
                      }
                      placeholder="From"
                      className="manual-input"
                    />
                    <input
                      value={experienceDraft.endDate}
                      onChange={(e) =>
                        setExperienceDraft({ ...experienceDraft, endDate: e.target.value })
                      }
                      placeholder="To"
                      className="manual-input"
                    />
                  </div>
                  <AddRowButton onClick={addExperience} label="Add experience" />
                </RepeatableSection>

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
                  <TagField
                    tags={interests}
                    onRemove={(t) => setInterests(interests.filter((x) => x !== t))}
                    typeahead={
                      <PlainTagInput
                        draft={interestDraft}
                        setDraft={setInterestDraft}
                        onAdd={addInterest}
                        placeholder="Add interest"
                      />
                    }
                  />
                </div>

                <div>
                  <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                    Target constraints
                  </p>
                  <TagField
                    tags={targetConstraints}
                    onRemove={(t) => setTargetConstraints(targetConstraints.filter((x) => x !== t))}
                    typeahead={
                      <PlainTagInput
                        draft={targetConstraintDraft}
                        setDraft={setTargetConstraintDraft}
                        onAdd={addTargetConstraint}
                        placeholder="Add constraint"
                      />
                    }
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

                        <RepeatableSection
                          title="Projects"
                          items={projects.map((item) => ({
                            title: item.title,
                            subtitle: item.description,
                            meta: [item.startDate, item.endDate].filter(Boolean).join("-"),
                          }))}
                          onRemove={(idx) => setProjects(projects.filter((_, i) => i !== idx))}
                        >
                          <div className="grid gap-2.5 sm:grid-cols-2">
                            <input
                              value={projectDraft.title}
                              onChange={(e) =>
                                setProjectDraft({ ...projectDraft, title: e.target.value })
                              }
                              placeholder="Project title"
                              className="manual-input"
                            />
                            <input
                              value={projectDraft.technologies}
                              onChange={(e) =>
                                setProjectDraft({ ...projectDraft, technologies: e.target.value })
                              }
                              placeholder="Technologies, comma-separated"
                              className="manual-input"
                            />
                            <input
                              value={projectDraft.description}
                              onChange={(e) =>
                                setProjectDraft({ ...projectDraft, description: e.target.value })
                              }
                              placeholder="Short description"
                              className="manual-input"
                            />
                            <div className="grid grid-cols-2 gap-2.5">
                              <input
                                value={projectDraft.startDate}
                                onChange={(e) =>
                                  setProjectDraft({ ...projectDraft, startDate: e.target.value })
                                }
                                placeholder="From"
                                className="manual-input"
                              />
                              <input
                                value={projectDraft.endDate}
                                onChange={(e) =>
                                  setProjectDraft({ ...projectDraft, endDate: e.target.value })
                                }
                                placeholder="To"
                                className="manual-input"
                              />
                            </div>
                          </div>
                          <AddRowButton onClick={addProject} label="Add project" />
                        </RepeatableSection>

                        <RepeatableSection
                          title="Certifications"
                          items={certifications.map((item) => ({
                            title: item.name,
                            subtitle: item.issuingOrganization,
                            meta: item.issueDate,
                          }))}
                          onRemove={(idx) =>
                            setCertifications(certifications.filter((_, i) => i !== idx))
                          }
                        >
                          <div className="grid gap-2.5 sm:grid-cols-3">
                            <input
                              value={certificationDraft.name}
                              onChange={(e) =>
                                setCertificationDraft({
                                  ...certificationDraft,
                                  name: e.target.value,
                                })
                              }
                              placeholder="Certification"
                              className="manual-input"
                            />
                            <input
                              value={certificationDraft.issuingOrganization}
                              onChange={(e) =>
                                setCertificationDraft({
                                  ...certificationDraft,
                                  issuingOrganization: e.target.value,
                                })
                              }
                              placeholder="Issuer"
                              className="manual-input"
                            />
                            <input
                              value={certificationDraft.issueDate}
                              onChange={(e) =>
                                setCertificationDraft({
                                  ...certificationDraft,
                                  issueDate: e.target.value,
                                })
                              }
                              placeholder="Year"
                              className="manual-input"
                            />
                          </div>
                          <AddRowButton onClick={addCertification} label="Add certification" />
                        </RepeatableSection>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <p className="text-[11.5px] leading-snug text-foreground/50">
                  You can review and edit everything on the next screen.
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

function RepeatableSection({
  title,
  items,
  onRemove,
  children,
}: {
  title: string;
  items: { title: string; subtitle?: string; meta?: string }[];
  onRemove: (idx: number) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-foreground/10 bg-white/45 p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
          {title}
        </p>
        <span className="text-[11px] tabular-nums text-foreground/45">{items.length}</span>
      </div>
      {items.length > 0 && (
        <div className="mb-2 flex flex-col gap-1.5">
          {items.map((item, idx) => (
            <div
              key={`${item.title}-${idx}`}
              className="flex items-center gap-2 rounded-xl bg-white/70 px-2.5 py-2 text-[12.5px]"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{item.title}</p>
                {item.subtitle && <p className="truncate text-foreground/55">{item.subtitle}</p>}
              </div>
              {item.meta && <span className="shrink-0 text-foreground/50">{item.meta}</span>}
              <button
                type="button"
                onClick={() => onRemove(idx)}
                className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-foreground/45 transition hover:bg-foreground/5 hover:text-foreground"
                aria-label={`Remove ${title.toLowerCase()} entry`}
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
      <div className="flex flex-col gap-2.5">{children}</div>
    </div>
  );
}

function AddRowButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex w-fit items-center gap-1.5 rounded-full bg-[color:var(--brand)]/10 px-3 py-1.5 text-[12.5px] font-medium text-[color:var(--brand)] transition hover:bg-[color:var(--brand)]/15"
    >
      <Plus size={12} />
      {label}
    </button>
  );
}

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
