import type { ComponentType, ReactNode } from "react";

/** Places in Core screens where Specialty Modules contribute UI (design doc §4.1). */
export type SectionSlotName = "patient-overview" | "patient-summary" | "clinical-data-tabs";

/** A Specialty Module's key, e.g. "oncology". */
export type ModuleKey = string;

/** What a screen is, for its placeholder and the screen inventory (design doc §5). */
export interface ScreenInfo {
  number?: number;
  title: string;
  purpose: string;
  /** The build stage that ships this screen (design doc §15). */
  stage: number;
  /** True once the screen is real, not a placeholder. Only built screens of shipped stages are shown. */
  built?: boolean;
}

export interface PatientTab {
  segment: string;
  label: string;
  screen: ScreenInfo;
  /** The slot this tab's screen exposes to Specialty Modules, if any. */
  slot?: SectionSlotName;
}

/**
 * The Practice's active modules, their sections and Patient tabs: the Builder's output from
 * GET /modules/active (#15). The backend decides *what* appears; the frontend supplies *how* it renders.
 */
export interface ModuleConfiguration {
  active_modules: ModuleKey[];
  sections: { module: ModuleKey; id: string; slot: string; title: string; order: number }[];
  patient_tabs: { module: ModuleKey; segment: string; label: string }[];
}

export const NO_MODULES: ModuleConfiguration = { active_modules: [], sections: [], patient_tabs: [] };

/** A rendered section: the API's section plus the module's renderer. */
export interface SectionDefinition {
  id: string;
  slot: SectionSlotName;
  title: string;
  order: number;
  render: () => ReactNode;
}

/**
 * A Condition a module extends (e.g. Oncology: a primary cancer → Cancer Diagnosis). "Add Condition" offers it,
 * as `label`, to Users who may enter `factKind`; the module's Form then records it.
 */
export interface ConditionExtension {
  factKind: string;
  label: string;
  Form: ComponentType<{ patientId: string; onSaved: () => void; onCancel: () => void }>;
}

/** What a module adds to a Treatment Course, e.g. Oncology's Line of Therapy or best response: a label and why. */
export interface CourseAnnotation {
  label: string;
  detail: string;
  overridden: boolean;
  /** Drawn as a status (colour, icon and label) rather than a plain chip, e.g. a best response. */
  badge?: ReactNode;
  /** The number behind the label (e.g. a Line of Therapy's line), for its editor. */
  value?: number;
}

/**
 * A module's view of the Core's Treatment Courses: `load` gives each course's annotation (by course id). With an
 * `edit`, Users who may enter its `factKind` can change one (a derived one like best response has none).
 */
export interface TreatmentCourseExtension {
  load: (patientId: string) => Promise<Record<string, CourseAnnotation>>;
  edit?: {
    factKind: string;
    /** The button that opens the editor, e.g. "Change line". */
    label: string;
    Editor: ComponentType<{ patientId: string; courseId: string; annotation: CourseAnnotation | undefined; onSaved: () => void; onCancel: () => void }>;
  };
}

/** A module's columns on the Patient List: `load` gives each Patient's values by column key (lists, shown joined). */
export interface PatientListColumns {
  load: () => Promise<Record<string, Record<string, string[]>>>;
  columns: { key: string; label: string }[];
  /** The column the list can be filtered by, if any. */
  filter?: { key: string; label: string };
}

/** One tile of the Patient Summary's at-a-glance strip: a label, the value (or nothing: "Not recorded") and one
 * line of context. `order` places it among the Core's tiles (Treatment 20, Next step 50). */
export interface GlanceTile {
  key: string;
  order: number;
  label: string;
  value: ReactNode | null;
  detail?: string | null;
}

/** A module's tiles on the Patient Summary's at-a-glance strip, e.g. Oncology's Diagnosis, Latest response, ECOG. */
export interface SummaryGlanceExtension {
  load: (patientId: string) => Promise<GlanceTile[]>;
}

/** A module's badge on the Core's Imaging Studies (by study id), e.g. Oncology's Response Assessment. */
export interface ImagingStudyExtension {
  load: (patientId: string) => Promise<Record<string, ReactNode>>;
}

/** A module's frontend: renderers for the sections and screens its backend declares. */
export interface ModuleManifest {
  key: ModuleKey;
  sections: Record<string, () => ReactNode>;
  patientTabs: Record<string, { screen: ScreenInfo; slot?: SectionSlotName }>;
  /** Its Clinical Data sub-tabs (sections in "clinical-data-tabs") that are built, with the part of their stage
   * that ships them (e.g. "4a"); the rest stay hidden. */
  builtSections?: Readonly<Record<string, string>>;
  conditionExtension?: ConditionExtension;
  treatmentCourseExtensions?: readonly TreatmentCourseExtension[];
  imagingStudyExtension?: ImagingStudyExtension;
  /** How many it has of each of its Clinical Data sub-tabs (by section id), for their counts. */
  clinicalDataCounts?: (patientId: string) => Promise<Record<string, number>>;
  /** Columns it adds to the Patient List, one of them perhaps a filter (e.g. Oncology's Cancer Type). */
  patientListColumns?: PatientListColumns;
  /** Its tiles on the Patient Summary's at-a-glance strip. */
  summaryGlance?: SummaryGlanceExtension;
  /** Its chip in the Patient header band, e.g. Oncology's "Colorectal cancer · Stage IIIB (dx)". */
  patientHeaderChip?: ComponentType<{ patientId: string }>;
}
