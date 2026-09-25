"use client";

import { PracticeDetailsForm } from "@/components/settings/PracticeDetailsForm";
import { SpecialtyModules } from "@/components/settings/SpecialtyModules";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { canChangeSettings, canSwitchModules, signOffName } from "@/lib/jobTitles";

/** Settings (design doc §5 screen 19). Stage 1: Practice details (#14) and Specialty Modules (#15). */
export default function SettingsPage() {
  const me = useSignedInUser();
  return (
    <div data-screen-label="Settings" className="flex w-full max-w-[900px] flex-col gap-4 px-5 pb-8 pt-3">
      <h1 className="m-0 text-xl font-semibold">Settings</h1>
      <PracticeDetailsForm canEdit={canChangeSettings(me.job_title)} />
      <SpecialtyModules canSwitch={canSwitchModules(me.job_title)} actor={signOffName(me)} />
    </div>
  );
}
