import { CircleAlert, CircleCheck, CircleX, KeyRound, type LucideIcon } from "lucide-react";
import { TONE, type Tone } from "@/components/ui/StatusPill";
import { listingOf, type PbsListing } from "@/lib/pbs";

/** docs/frontend-design.md §4.1: Unrestricted green; Restricted and Authority Required amber; Not Listed red. */
const LISTING: Record<PbsListing, { label: string; tone: Tone; icon: LucideIcon }> = {
  unrestricted: { label: "Unrestricted", tone: "pos", icon: CircleCheck },
  restricted: { label: "Restricted", tone: "cau", icon: CircleAlert },
  authority_required: { label: "Authority Required", tone: "cau", icon: KeyRound },
  not_listed: { label: "Not Listed", tone: "neg", icon: CircleX },
};

/** A PBS Listing for one indication: always icon, label and colour (§3 "colour never works alone"). */
export function PbsListingBadge({ level }: { level: string }) {
  const { listing, streamlined } = listingOf(level);
  const { label, tone, icon: Icon } = LISTING[listing];
  return (
    <span className={`inline-flex w-fit items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${TONE[tone]}`}>
      <Icon aria-hidden className="h-3 w-3" />
      {streamlined ? `${label} (streamlined)` : label}
    </span>
  );
}
