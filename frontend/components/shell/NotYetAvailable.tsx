import Link from "next/link";

/** A screen whose build stage hasn't shipped (design doc §15): friendly, not a placeholder. */
export function NotYetAvailable({ title, home }: { title: string; home: string }) {
  return (
    <div className="flex flex-col gap-2 px-5 py-10">
      <h1 className="m-0 text-xl font-semibold">Not available yet</h1>
      <p className="m-0 max-w-[60ch] text-[13px] text-muted-foreground">{title} isn&apos;t part of Vigil yet. It arrives in a later stage of the build.</p>
      <Link href={home} className="text-[13px] font-medium text-primary">Go to your home page</Link>
    </div>
  );
}
