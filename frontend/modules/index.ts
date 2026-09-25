import type { ModuleManifest } from "@/lib/modules/types";
import { oncologyManifest } from "./oncology/manifest";

/** Installed Specialty Modules. The only place that names a module; Core code reads the registry. */
export const INSTALLED_MODULES: readonly ModuleManifest[] = [oncologyManifest];
