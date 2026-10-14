// Plain-language descriptions of what happened to a request, for the run view.

import { formatStay } from "./format";
import type { RequestDetail } from "./types";

type Reply = { target?: string; flags?: string[]; situation?: string };

/** One sentence saying where the request stands and why. */
export function outcome(detail: RequestDetail): string {
  const reply = detail.steps.reply as Reply | undefined;
  const approval = detail.approvals.at(-1);
  switch (detail.status) {
    case "sent":
      if (!approval) return "Sent automatically. Every check passed and the reply promised nothing more.";
      if (approval.action === "reject") return `Declined by ${approval.staff_name}. A polite decline was sent.`;
      if (approval.action === "edit_and_approve") return `Sent after ${approval.staff_name} edited the reply.`;
      return `Sent after ${approval.staff_name} approved the reply.`;
    case "needs_review":
      return reply?.flags?.length ? `Waiting for you: ${flagText(reply.flags[0])}.` : "Waiting for you.";
    case "failed":
      return `Stopped while ${detail.failed_step ?? "working"}. It can be retried.`;
    default:
      return "Working on it.";
  }
}

/** "came through resolving: not_attempted (needs a person: intake: message contains …)" → readable. */
export function flagText(flag: string): string {
  const reason = flag.match(/needs a person: (.*)\)$/)?.[1];
  if (reason) return reason.replace(/^(intake|records): /, "").split("; ")[0];
  if (flag.startsWith("came through resolving: proposed")) return "the request needed other options";
  return flag.replace(/^reply: /, "the reply ").replace(/_/g, " ");
}

type Option = Record<string, unknown> & { kind: string; verified?: boolean; remaining_problems?: string[] };

export function optionText(option: Option): string {
  switch (option.kind) {
    case "alternative_dates":
      return `Other dates, ${formatStay(String(option.start_date), String(option.end_date))}`;
    case "larger_kennel":
      return `A ${String(option.size_class)} kennel for the same dates`;
    case "vaccine_update":
      return `An updated ${(option.vaccines as string[]).join(" and ")} record`;
    default:
      return option.kind;
  }
}
