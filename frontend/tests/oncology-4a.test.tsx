import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/clinical-data", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));
const clinical = vi.hoisted(() => ({ fetchEntryRights: vi.fn() }));
vi.mock("@/lib/clinical", async (importOriginal) => ({ ...(await importOriginal<object>()), ...clinical }));

import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { BiomarkerChip, markerName, resultText } from "@/modules/oncology/Biomarkers";
import { cnsLine } from "@/modules/oncology/Observations";
import { Recurrences, RecurrenceStatus, type RecurrenceRow } from "@/modules/oncology/Recurrences";
import { isPartShipped } from "@/lib/stages";
import type { CancerDiagnosisRow } from "@/modules/oncology/CancerDiagnoses";
import { userWith } from "./fixtures";

const DIAGNOSIS = { id: "cd-1", name: "Breast cancer" } as CancerDiagnosisRow;
const SUSPECTED: RecurrenceRow = {
  id: "r-1", cancer_diagnosis_id: "cd-1", cancer_diagnosis_name: "Breast cancer", status: "suspected", detected_on: "2026-02-10",
  extent: "distant", sites: ["liver"], new_cancer_diagnosis_id: null, resolved: null, entered: null,
};

describe("Biomarker chips", () => {
  it("name the marker and variant, with the result", () => {
    expect(markerName({ name: "EGFR", variant: "exon 19 deletion" })).toBe("EGFR exon 19 deletion");
    expect(resultText({ result: "positive", value_num: "60", value_unit: "% TPS" })).toBe("positive (60 % TPS)");
    expect(resultText({ result: null, value_num: null, value_unit: null })).toBe("—");
  });

  it("say only 'Results differ' when they do: never a cause or an action", () => {
    render(<BiomarkerChip chip={{ name: "HER2", variant: null, result: "negative", value_num: null, value_unit: null, differs: true }} />);
    const chip = screen.getByText("HER2").parentElement!;
    expect(chip).toHaveTextContent("HER2 negativeResults differ");
    expect(chip).toHaveClass("text-cau");
    expect(chip.textContent).not.toMatch(/new primary|re-biopsy|consider/i);
  });
});

describe("Recurrences", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.request.mockResolvedValue({ ...SUSPECTED, status: "confirmed" });
  });

  function renderAs(canResolve: boolean) {
    const onChanged = vi.fn();
    render(
      <ViewerProvider initialUser={userWith(canResolve ? "clinician" : "trial_coordinator")}>
        <Recurrences patientId="pt-1" diagnosis={DIAGNOSIS} recurrences={[SUSPECTED]} canRecord canResolve={canResolve} onChanged={onChanged} />
      </ViewerProvider>,
    );
    return onChanged;
  }

  it("lets a clinician confirm, reclassify or rule out a suspected one", async () => {
    const onChanged = renderAs(true);
    expect(screen.getByText(/Distant: liver · detected 10\/02\/2026/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith("/patients/pt-1/recurrences/r-1/confirm", { method: "POST" }));
    expect(onChanged).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "New primary instead" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Rule out" }));
    expect(await screen.findByRole("dialog", { name: "Rule out this recurrence" })).toBeInTheDocument();
  });

  it("prefills the new primary from the recurrence", async () => {
    api.request.mockImplementation(async (path: string) => (path === "/cancer-types" ? [] : SUSPECTED));
    renderAs(true);
    fireEvent.click(screen.getByRole("button", { name: "New primary instead" }));
    const form = await screen.findByRole("form", { name: "New Cancer Diagnosis" });
    expect(within(form).getByLabelText("Date of diagnosis")).toHaveValue("2026-02-10");
    expect(within(form).getByLabelText("Primary site")).toHaveValue("liver");
  });

  it("shows a trial coordinator the recurrence but not the clinician's decisions", () => {
    renderAs(false);
    expect(screen.getByText("Suspected")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Record a suspected recurrence" })).toBeInTheDocument();
  });
});

describe("CNS status", () => {
  it("reads in plain words", () => {
    const row = { id: "c", assessed_on: "2026-09-20", present: true, lesion_count: 2, locations: [], entered: null };
    expect(cnsLine(row as never)).toBe("CNS disease present: 2 lesions (20/09/2026)");
    expect(cnsLine({ ...row, present: false } as never)).toBe("No CNS disease (20/09/2026)");
  });
});


describe("Stage 4 ships in parts", () => {
  it("shows 4a now, and 4b and 4c only when upcoming screens are revealed", () => {
    expect(isPartShipped("4a")).toBe(true);
    expect(isPartShipped("4b")).toBe(false);
    expect(isPartShipped("4c")).toBe(false);
    expect(isPartShipped("4c", true)).toBe(true);
  });
});

describe("A Recurrence's status", () => {
  it("has an icon as well as its colour and label", () => {
    const { container } = render(<RecurrenceStatus status="suspected" />);
    expect(container).toHaveTextContent("Suspected");
    expect(container.querySelector("svg")).not.toBeNull();
  });
});
