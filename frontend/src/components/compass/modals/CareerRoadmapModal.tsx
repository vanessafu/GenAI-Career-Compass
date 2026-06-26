import { DeepDiveModal, ModalBlock } from "./DeepDiveModal";
import type { CareerPathReport } from "@/lib/api";
import type { RoleView } from "@/types";

export function CareerRoadmapModal({
  role,
  report,
  loading,
  error,
  open,
  onClose,
}: {
  role: RoleView;
  report: CareerPathReport | null;
  loading: boolean;
  error: string | null;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <DeepDiveModal open={open} onClose={onClose} title={role.title} subtitle="Career roadmap" wide>
      {loading && (
        <ModalBlock className="mb-6">
          <p className="text-[13px] leading-relaxed text-foreground/60">Preparing roadmap...</p>
        </ModalBlock>
      )}

      {error && (
        <ModalBlock className="mb-6 border-l-2 border-red-300 pl-3">
          <p className="text-[13px] leading-relaxed text-red-700">{error}</p>
        </ModalBlock>
      )}

      {report && <RoadmapContent report={report} />}
    </DeepDiveModal>
  );
}

function RoadmapContent({ report }: { report: CareerPathReport }) {
  const readiness = percent(
    report.readiness_score || report.requirement_breakdown.overall_readiness,
  );
  const milestones = [...report.milestones].sort((a, b) => a.order - b.order);

  return (
    <>
      <ModalBlock className="mb-5">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-foreground/10 pb-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/45">Readiness</p>
            <p className="font-display text-4xl tracking-tight text-[color:var(--brand-deep)]">
              {readiness}%
            </p>
          </div>
          {report.estimated_timeline && (
            <div className="text-right">
              <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/45">Timeline</p>
              <p className="text-[13px] font-medium text-foreground/80">
                {report.estimated_timeline}
              </p>
            </div>
          )}
        </div>
      </ModalBlock>

      <ModalBlock className="mb-6">
        <div className="grid gap-3 lg:grid-cols-[220px_minmax(0,1fr)_220px]">
          <EndpointPanel title="Current profile" body={report.current_profile_summary} />

          <div className="min-w-0">
            <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
              Milestones
            </p>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {milestones.map((milestone) => (
                <div
                  key={`${milestone.order}-${milestone.title}`}
                  className="min-w-[220px] flex-1 rounded-2xl border border-foreground/10 bg-white/70 p-3"
                >
                  <span className="text-[11px] font-medium text-[color:var(--brand-deep)]">
                    Step {milestone.order}
                  </span>
                  <h4 className="mt-1 text-[14px] font-medium leading-snug text-foreground/85">
                    {milestone.title}
                  </h4>
                  {milestone.timeline && (
                    <p className="mt-1 text-[11.5px] text-foreground/50">{milestone.timeline}</p>
                  )}
                  {milestone.rationale && (
                    <p className="mt-2 text-[12.5px] leading-relaxed text-foreground/65">
                      {milestone.rationale}
                    </p>
                  )}
                  <ChipList items={[...milestone.skills, ...milestone.projects]} />
                </div>
              ))}
            </div>
          </div>

          <EndpointPanel title="Target role" body={report.target_role} items={report.top_gaps} />
        </div>
      </ModalBlock>

      <div className="grid gap-4 lg:grid-cols-2">
        <ListBlock title="Top gaps" items={report.top_gaps} />
        <ListBlock title="Skills to learn" items={report.skills_to_learn} />
        <ListBlock title="Recommended projects" items={report.recommended_projects} />
        <ListBlock title="Certifications" items={report.certifications} />
      </div>

      <RequirementBreakdown report={report} />
    </>
  );
}

function EndpointPanel({
  title,
  body,
  items = [],
}: {
  title: string;
  body: string;
  items?: string[];
}) {
  return (
    <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.03] p-3">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">{title}</p>
      <p className="text-[13px] leading-relaxed text-foreground/75">{body}</p>
      <ChipList items={items} />
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  const shown = unique(items);
  if (shown.length === 0) return null;
  return (
    <ModalBlock className="mb-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">{title}</p>
      <ChipList items={shown} />
    </ModalBlock>
  );
}

function RequirementBreakdown({ report }: { report: CareerPathReport }) {
  const breakdown = report.requirement_breakdown;
  const missing = unique(breakdown.skills.skill_gaps.map((gap) => gap.required_skill || gap.skill));
  const certs = unique(
    [...breakdown.certifications.missing, ...breakdown.certifications.missing_certifications].map(
      (gap) => gap.required_certification || gap.name || gap.normalized_name,
    ),
  );

  return (
    <ModalBlock className="mt-1 border-t border-foreground/10 pt-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
        Requirement breakdown
      </p>
      <div className="grid gap-4 lg:grid-cols-3">
        <RequirementStat label="Matched skills" items={breakdown.skills.matched_skills} />
        <RequirementStat label="Skill gaps" items={missing} />
        <RequirementStat label="Certification gaps" items={certs} />
      </div>
    </ModalBlock>
  );
}

function RequirementStat({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <p className="mb-2 text-[12px] font-medium text-foreground/75">{label}</p>
      <ChipList items={items} empty="None visible" />
    </div>
  );
}

function ChipList({ items, empty }: { items: string[]; empty?: string }) {
  const shown = unique(items);
  if (shown.length === 0) {
    return empty ? <p className="text-[12px] text-foreground/45">{empty}</p> : null;
  }
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {shown.map((item) => (
        <span
          key={item}
          className="rounded-full border border-foreground/10 bg-white/70 px-2.5 py-1 text-[12px] text-foreground/70"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function unique(items: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of items) {
    const cleaned = item?.trim();
    if (!cleaned || seen.has(cleaned.toLowerCase())) continue;
    seen.add(cleaned.toLowerCase());
    out.push(cleaned);
  }
  return out;
}

function percent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  const normalized = value > 1 ? value / 100 : value;
  return Math.round(Math.max(0, Math.min(1, normalized)) * 100);
}
