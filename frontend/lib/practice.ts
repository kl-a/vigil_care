import { request, type Schemas } from "./api";

export type PracticeDetails = Schemas["PracticeDetails"];
export type PracticeChange = Schemas["PracticeChange"];

export const fetchPractice = () => request<PracticeDetails>("/practice");
export const changePractice = (change: PracticeChange) =>
  request<PracticeDetails>("/practice", { method: "PATCH", body: JSON.stringify(change) });
