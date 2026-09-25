/** A typed latitude or longitude: empty clears it, anything else must be a number. */
export function parseCoordinate(text: string): number | null | "invalid" {
  const value = text.trim();
  if (value === "") return null;
  const number = Number(value);
  return Number.isNaN(number) ? "invalid" : number;
}

export const COORDINATES_MUST_BE_NUMBERS = "Latitude and longitude must be numbers.";
