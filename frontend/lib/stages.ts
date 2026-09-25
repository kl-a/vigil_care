/**
 * Build stages (design doc §15). A screen appears once its stage has shipped; in dev, "Show upcoming
 * screens" reveals the rest as placeholders.
 *
 * Raise SHIPPED_STAGE when a stage's demo is ready (docs/build-order.md).
 */
export const SHIPPED_STAGE = 1;

export function isShipped(stage: number): boolean {
  return stage <= SHIPPED_STAGE;
}

/** Whether a screen of this stage is shown: shipped, or upcoming screens revealed (dev only). */
export function isVisible(stage: number, showUpcoming: boolean): boolean {
  return isShipped(stage) || showUpcoming;
}
