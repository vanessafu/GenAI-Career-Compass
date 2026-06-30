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
import {
  Upload,
  FileText,
  X,
  Plus,
  ArrowRight,
  Sparkles,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Calendar,
} from "lucide-react";
import { LoadingPanel } from "../ui/LoadingPanel";

const PARSE_STEPS = ["Reading your CV", "Privacy-stripping data", "Generating identity"];
const MANUAL_STEPS = ["Structuring your profile", "Privacy-stripping data", "Generating identity"];

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

const DEGREE_LEVELS = [
  "B.Sc.",
  "M.Sc.",
  "B.A.",
  "M.A.",
  "B.Eng.",
  "M.Eng.",
  "PhD",
  "MBA",
  "Abitur",
  "Bootcamp",
  "Other",
];

const LANGUAGE_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "Native"];

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
  const [manualOpen, setManualOpen] = useState(false);
  const manualCardRef = useRef<HTMLDivElement | null>(null);

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
  const [skills, setSkills] = useState<string[]>([]);
  const [skillDraft, setSkillDraft] = useState("");
  const [interests, setInterests] = useState<string[]>([]);
  const [interestDraft, setInterestDraft] = useState("");

  // Tier 2 — add more context (collapsed by default)
  const [showMore, setShowMore] = useState(false);
  const [summary, setSummary] = useState("");
  const [softSkills, setSoftSkills] = useState<string[]>([]);
  const [softSkillDraft, setSoftSkillDraft] = useState("");
  const [languages, setLanguages] = useState<{ name: string; level: string }[]>([]);
  const [languageDraft, setLanguageDraft] = useState({ name: "", level: "" });
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

  useEffect(() => {
    if (!manualOpen) return;
    const id = window.setTimeout(() => {
      manualCardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 40);
    return () => window.clearTimeout(id);
  }, [manualOpen]);

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

  const addLanguage = () => {
    const name = languageDraft.name.trim();
    if (!name || languages.some((item) => item.name.toLowerCase() === name.toLowerCase())) return;
    setLanguages([...languages, { name, level: languageDraft.level.trim() }]);
    setLanguageDraft({ name: "", level: "" });
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
    if (!role.trim()) {
      setFormError("Add your current role.");
      return;
    }
    if (skills.length === 0) {
      setFormError("Add at least one technical skill.");
      return;
    }
    if (interests.length === 0) {
      setFormError("Add at least one interest.");
      return;
    }

    // Flush any typed-but-not-added drafts so nothing is lost on submit.
    const educationOut = educationDraft.degree.trim()
      ? [
          ...education,
          {
            degree: educationDraft.degree.trim(),
            institution: educationDraft.institution.trim(),
            fieldOfStudy: educationDraft.fieldOfStudy.trim(),
            startDate: educationDraft.startDate.trim(),
            endDate: educationDraft.endDate.trim(),
          },
        ]
      : education;
    const experienceOut = experienceDraft.role.trim()
      ? [
          ...experience,
          {
            role: experienceDraft.role.trim(),
            organization: experienceDraft.organization.trim(),
            startDate: experienceDraft.startDate.trim(),
            endDate: experienceDraft.endDate.trim(),
          },
        ]
      : experience;
    const projectsOut = projectDraft.title.trim()
      ? [
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
        ]
      : projects;
    const certificationsOut = certificationDraft.name.trim()
      ? [
          ...certifications,
          {
            name: certificationDraft.name.trim(),
            issuingOrganization: certificationDraft.issuingOrganization.trim(),
            issueDate: certificationDraft.issueDate.trim(),
          },
        ]
      : certifications;
    const languagesOut = languageDraft.name.trim()
      ? [...languages, { name: languageDraft.name.trim(), level: languageDraft.level.trim() }]
      : languages;

    setFormError(null);
    setSteps(MANUAL_STEPS);
    setParsing(true);
    setDone(false);
    startProgress(MANUAL_PROFILE_PROGRESS);

    const ok = await submitManualProfile({
      currentRole: role,
      education: educationOut,
      experience: experienceOut,
      skills,
      interests,
      softSkills,
      languages: languagesOut,
      projects: projectsOut,
      certifications: certificationsOut,
      summary,
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
    <div
      className={cn(
        "relative flex w-full flex-col items-stretch px-6 sm:px-10 lg:px-16",
        manualOpen
          ? "min-h-dvh overflow-x-hidden pb-10 pt-[max(5rem,calc(env(safe-area-inset-top)+4.5rem))] sm:pt-[5.5rem]"
          : "h-dvh overflow-hidden pb-7 pt-[max(5rem,calc(env(safe-area-inset-top)+4.5rem))] sm:pt-[5.25rem]",
      )}
    >
      <div
        className={cn(
          "mx-auto flex w-full max-w-[1180px] flex-col gap-5",
          manualOpen ? "min-h-0" : "min-h-0 flex-1",
        )}
      >
        {/* Headline — transform-only animation, glides centered when loading appears. */}
        <motion.div
          animate={{ scale: parsing ? 0.86 : 1, y: parsing ? 4 : 0 }}
          transition={{ type: "spring", stiffness: 180, damping: 30, mass: 0.9 }}
          style={{ transformOrigin: parsing ? "center top" : "left top", willChange: "transform" }}
          className={cn(
            "flex shrink-0 flex-col transition-[align-items,text-align] duration-500",
            parsing ? "items-center text-center" : "items-start max-w-4xl",
          )}
        >
          <h1 className="font-display text-balance text-[clamp(2.1rem,5.3vw,3.55rem)] leading-[0.98] tracking-[-0.01em]">
            Let us map your expertise to{" "}
            <span
              className="italic"
              style={{
                background: "var(--gradient-warm)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              future opportunities
            </span>
          </h1>
          <motion.p
            animate={{
              opacity: parsing ? 0 : 1,
              height: parsing ? 0 : "auto",
              marginTop: parsing ? 0 : 12,
            }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
            className="max-w-[88ch] overflow-hidden text-[15px] leading-relaxed text-foreground/65"
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
              className={cn(
                "grid w-full gap-5 md:grid-cols-2",
                manualOpen ? "items-start" : "min-h-0 flex-1 items-stretch",
              )}
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
                  "liquid-glass flex flex-col rounded-3xl p-7 transition-colors",
                  manualOpen ? "min-h-[520px]" : "h-full min-h-0",
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

                <motion.label
                  animate={drag ? { scale: 1.01 } : { scale: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  className={cn(
                    "mt-4 flex flex-1 cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border border-dashed p-6 text-center transition-colors",
                    drag
                      ? "border-[color:var(--brand)]/60 bg-[color:var(--brand)]/[0.06]"
                      : "border-foreground/15 bg-white/55",
                  )}
                >
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
                  <motion.div
                    animate={drag ? { y: -2 } : { y: 0 }}
                    className="grid h-14 w-14 place-items-center rounded-2xl text-white"
                    style={{ background: "var(--gradient-warm)" }}
                  >
                    <Upload size={20} />
                  </motion.div>
                  <p className="text-[14.5px] font-medium">{fileName ?? "Drag & drop your CV"}</p>
                </motion.label>

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
                ref={manualCardRef}
                layout
                transition={{ type: "spring", stiffness: 260, damping: 22 }}
                onClick={() => {
                  if (!manualOpen) setManualOpen(true);
                }}
                className={cn(
                  "liquid-glass flex flex-col rounded-3xl p-7",
                  manualOpen ? "gap-3.5" : "h-full min-h-0 cursor-pointer gap-3.5 overflow-hidden",
                )}
                aria-expanded={manualOpen}
              >
                <div>
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="font-display text-[22px] tracking-tight">Fill it in manually</h3>
                    <span className="inline-flex shrink-0 items-center rounded-full bg-[color:var(--brand)]/10 px-2 py-0.5 text-[10.5px] font-medium text-[color:var(--brand)]">
                      Quick form
                    </span>
                  </div>
                  {!manualOpen && (
                    <p className="mt-1 max-w-sm text-[13.5px] leading-relaxed text-foreground/60">
                      Answer a few fields yourself instead of uploading a CV.
                    </p>
                  )}
                </div>

                <motion.div
                  animate={{ height: manualOpen ? "auto" : "100%" }}
                  transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                  onFocusCapture={() => {
                    if (!manualOpen) setManualOpen(true);
                  }}
                  onClickCapture={() => {
                    if (!manualOpen) setManualOpen(true);
                  }}
                  className={cn(
                    "relative flex flex-col gap-3.5",
                    manualOpen ? "overflow-visible" : "min-h-0 flex-1 overflow-hidden",
                  )}
                >
                  <div className="grid gap-2.5">
                    <AutocompleteInput
                      label="Current role"
                      required
                      value={role}
                      onChange={setRole}
                      presets={ROLE_PRESETS}
                      placeholder="e.g. Senior Backend Developer"
                    />
                  </div>

                  <RepeatableSection
                    title="Education"
                    items={education.map((item) => ({
                      title: [item.degree, item.fieldOfStudy].filter(Boolean).join(" — "),
                      subtitle: item.institution,
                      meta: formatRange(item.startDate, item.endDate),
                    }))}
                    onRemove={(idx) => setEducation(education.filter((_, i) => i !== idx))}
                  >
                    <div className="grid gap-2.5 sm:grid-cols-2">
                      <InlineAutocomplete
                        value={educationDraft.degree}
                        onChange={(value) =>
                          setEducationDraft({ ...educationDraft, degree: value })
                        }
                        presets={DEGREE_LEVELS}
                        placeholder="Degree, e.g. M.Sc."
                      />
                      <input
                        value={educationDraft.fieldOfStudy}
                        onChange={(e) =>
                          setEducationDraft({ ...educationDraft, fieldOfStudy: e.target.value })
                        }
                        placeholder="Field of study, e.g. Robotics"
                        className="manual-input"
                      />
                      <input
                        value={educationDraft.institution}
                        onChange={(e) =>
                          setEducationDraft({ ...educationDraft, institution: e.target.value })
                        }
                        placeholder="Institution, e.g. TU Munich"
                        className="manual-input sm:col-span-2"
                      />
                      <MonthRange
                        start={educationDraft.startDate}
                        end={educationDraft.endDate}
                        onStart={(value) =>
                          setEducationDraft({ ...educationDraft, startDate: value })
                        }
                        onEnd={(value) => setEducationDraft({ ...educationDraft, endDate: value })}
                        className="sm:col-span-2"
                      />
                    </div>
                    <AddRowButton onClick={addEducation} label="Add education" />
                  </RepeatableSection>

                  <RepeatableSection
                    title="Experience"
                    items={experience.map((item) => ({
                      title: item.role,
                      subtitle: item.organization,
                      meta: formatRange(item.startDate, item.endDate, "Present"),
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
                      <MonthRange
                        start={experienceDraft.startDate}
                        end={experienceDraft.endDate}
                        onStart={(value) =>
                          setExperienceDraft({ ...experienceDraft, startDate: value })
                        }
                        onEnd={(value) =>
                          setExperienceDraft({ ...experienceDraft, endDate: value })
                        }
                        className="sm:col-span-2"
                      />
                    </div>
                    <AddRowButton onClick={addExperience} label="Add experience" />
                  </RepeatableSection>

                  <div>
                    <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
                      Technical skills <RequiredMark />
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
                      What are you drawn to? <RequiredMark />
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

                          <RepeatableSection
                            title="Languages"
                            items={languages.map((item) => ({
                              title: item.name,
                              meta: item.level,
                            }))}
                            onRemove={(idx) =>
                              setLanguages(languages.filter((_, i) => i !== idx))
                            }
                          >
                            <div className="grid gap-2.5 sm:grid-cols-2">
                              <input
                                value={languageDraft.name}
                                onChange={(e) =>
                                  setLanguageDraft({ ...languageDraft, name: e.target.value })
                                }
                                placeholder="Language, e.g. English"
                                className="manual-input"
                              />
                              <InlineAutocomplete
                                value={languageDraft.level}
                                onChange={(value) =>
                                  setLanguageDraft({ ...languageDraft, level: value })
                                }
                                presets={LANGUAGE_LEVELS}
                                placeholder="Level, e.g. C2"
                              />
                            </div>
                            <AddRowButton onClick={addLanguage} label="Add language" />
                          </RepeatableSection>

                          <RepeatableSection
                            title="Projects"
                            items={projects.map((item) => ({
                              title: item.title,
                              subtitle: item.description,
                              meta: formatRange(item.startDate, item.endDate),
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
                              <MonthRange
                                start={projectDraft.startDate}
                                end={projectDraft.endDate}
                                onStart={(value) =>
                                  setProjectDraft({ ...projectDraft, startDate: value })
                                }
                                onEnd={(value) =>
                                  setProjectDraft({ ...projectDraft, endDate: value })
                                }
                              />
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
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <p className="text-[11.5px] leading-snug text-foreground/50">
                    <span className="text-[color:var(--brand)]">*</span> required field. You can
                    review and edit everything on the next screen.
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
                  {!manualOpen && (
                    <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/5 bg-gradient-to-b from-white/0 via-white/45 to-white/95" />
                  )}
                </motion.div>
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

function RequiredMark() {
  return (
    <span className="text-[color:var(--brand)]" aria-hidden="true">
      *
    </span>
  );
}

const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** Render a `YYYY-MM` value as a friendly "Mar 2024" label (or the raw value). */
function formatMonthLabel(value: string): string {
  const match = value.trim().match(/^(\d{4})-(\d{2})$/);
  if (!match) return value.trim();
  const monthIndex = Number(match[2]) - 1;
  const month = MONTH_LABELS[monthIndex] ?? match[2];
  return `${month} ${match[1]}`;
}

/** Join a start/end month range with a single dash, skipping empty parts. */
function formatRange(start: string, end: string, endFallback = ""): string {
  const startLabel = formatMonthLabel(start);
  const endLabel = end.trim() ? formatMonthLabel(end) : endFallback;
  if (startLabel && endLabel) return `${startLabel} – ${endLabel}`;
  return startLabel || endLabel;
}

function MonthRange({
  start,
  end,
  onStart,
  onEnd,
  className,
}: {
  start: string;
  end: string;
  onStart: (v: string) => void;
  onEnd: (v: string) => void;
  className?: string;
}) {
  return (
    <div className={cn("grid grid-cols-2 gap-2.5", className)}>
      <MonthYearPicker value={start} onChange={onStart} placeholder="From" />
      <MonthYearPicker value={end} onChange={onEnd} placeholder="To" allowPresent />
    </div>
  );
}

/** Modern month/year picker: a styled trigger that opens a compact popover. */
function MonthYearPicker({
  value,
  onChange,
  placeholder,
  allowPresent,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  allowPresent?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const parsed = value.trim().match(/^(\d{4})-(\d{2})$/);
  const selectedYear = parsed ? Number(parsed[1]) : null;
  const selectedMonth = parsed ? Number(parsed[2]) : null;
  const [viewYear, setViewYear] = useState(selectedYear ?? new Date().getFullYear());

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          setViewYear(selectedYear ?? new Date().getFullYear());
          setOpen((v) => !v);
        }}
        className="manual-input flex items-center justify-between gap-2 text-left"
      >
        <span className={cn(value.trim() ? "text-foreground" : "text-foreground/40")}>
          {value.trim() ? formatMonthLabel(value) : (placeholder ?? "Select")}
        </span>
        <Calendar size={14} className="shrink-0 text-foreground/40" />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden="true" />
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.98 }}
              transition={{ duration: 0.14 }}
              className="absolute left-0 top-full z-40 mt-1.5 w-56 rounded-2xl border border-foreground/10 bg-white/95 p-2.5 shadow-xl backdrop-blur"
            >
              <div className="mb-2 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setViewYear((y) => y - 1)}
                  className="grid h-7 w-7 place-items-center rounded-lg text-foreground/60 transition hover:bg-foreground/5"
                  aria-label="Previous year"
                >
                  <ChevronLeft size={15} />
                </button>
                <span className="text-[13.5px] font-semibold tabular-nums">{viewYear}</span>
                <button
                  type="button"
                  onClick={() => setViewYear((y) => y + 1)}
                  className="grid h-7 w-7 place-items-center rounded-lg text-foreground/60 transition hover:bg-foreground/5"
                  aria-label="Next year"
                >
                  <ChevronRight size={15} />
                </button>
              </div>
              <div className="grid grid-cols-3 gap-1">
                {MONTH_LABELS.map((m, i) => {
                  const isSelected = selectedYear === viewYear && selectedMonth === i + 1;
                  return (
                    <button
                      key={m}
                      type="button"
                      onClick={() => {
                        onChange(`${viewYear}-${String(i + 1).padStart(2, "0")}`);
                        setOpen(false);
                      }}
                      className={cn(
                        "rounded-lg py-1.5 text-[12.5px] transition",
                        isSelected
                          ? "text-white"
                          : "text-foreground/75 hover:bg-[color:var(--brand)]/10",
                      )}
                      style={isSelected ? { background: "var(--gradient-warm)" } : undefined}
                    >
                      {m}
                    </button>
                  );
                })}
              </div>
              <div className="mt-2 flex items-center justify-between border-t border-foreground/10 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    onChange("");
                    setOpen(false);
                  }}
                  className="rounded-md px-2 py-1 text-[12px] text-foreground/55 transition hover:bg-foreground/5"
                >
                  {allowPresent ? "Present" : "Clear"}
                </button>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="rounded-md px-2 py-1 text-[12px] font-medium text-[color:var(--brand-deep)] transition hover:bg-[color:var(--brand)]/10"
                >
                  Done
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
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

/** Plain input with a styled autocomplete popover but no label above it. */
function InlineAutocomplete({
  value,
  onChange,
  presets,
  placeholder,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  presets: string[];
  placeholder?: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const matches = presets
    .filter((p) => p.toLowerCase().includes(value.toLowerCase()) && p !== value)
    .slice(0, 15);
  return (
    <div className={cn("relative", className)}>
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
    </div>
  );
}

function AutocompleteInput({
  label,
  value,
  onChange,
  presets,
  placeholder,
  required,
  className,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  presets: string[];
  placeholder?: string;
  required?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const matches = presets
    .filter((p) => p.toLowerCase().includes(value.toLowerCase()) && p !== value)
    .slice(0, 15);
  return (
    <label className={cn("relative block", className)}>
      <span className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-[0.12em] text-foreground/55">
        {label} {required && <RequiredMark />}
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
            className="removable-chip removable-chip--brand inline-flex max-w-full items-center rounded-full bg-[color:var(--brand)]/10 px-2.5 py-0.5 text-[12px] text-[color:var(--brand)]"
          >
            <span className="removable-chip-label">{t}</span>
            <button
              type="button"
              onClick={() => onRemove(t)}
              className="removable-chip-remove"
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
