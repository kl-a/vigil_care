import type { ScreenInfo } from "./modules/types";

/**
 * Build stages (design doc §15). A screen appears once it is built and its stage has shipped; in dev,
 * "Show upcoming screens" reveals the rest as placeholders.
 *
 * Raise SHIPPED_STAGE when a stage's demo is ready (docs/build-order.md). Mark a screen `built` when
 * it stops being a placeholder.
 */
export const SHIPPED_STAGE = 3;

export function isShipped(stage: number): boolean {
  return stage <= SHIPPED_STAGE;
}

/** Shown to everyone: built, in a shipped stage. */
export function isReleased(screen: Pick<ScreenInfo, "stage" | "built">): boolean {
  return isShipped(screen.stage) && screen.built === true;
}

/** Shown to this viewer: released, or upcoming screens revealed (dev only). */
export function isVisible(screen: Pick<ScreenInfo, "stage" | "built">, showUpcoming: boolean): boolean {
  return isReleased(screen) || showUpcoming;
}
