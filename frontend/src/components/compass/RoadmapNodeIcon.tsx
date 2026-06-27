import type { LucideIcon } from "lucide-react";
import { Award, Briefcase, Flag, Folder, Network, Rocket, Terminal, Trophy } from "lucide-react";
import type { RoadmapNodeKind } from "@/lib/roadmapPreview";

export function RoadmapNodeIcon({ kind, size = 16 }: { kind: RoadmapNodeKind; size?: number }) {
  const Icon = iconForRoadmapNode(kind);
  return <Icon aria-hidden size={size} strokeWidth={1.9} />;
}

function iconForRoadmapNode(kind: RoadmapNodeKind): LucideIcon {
  if (kind === "start") return Flag;
  if (kind === "target") return Trophy;

  switch (kind) {
    case "role":
      return Network;
    case "project":
      return Folder;
    case "certification":
      return Award;
    case "experience":
      return Briefcase;
    case "skill":
      return Terminal;
    case "milestone":
    default:
      return Rocket;
  }
}
