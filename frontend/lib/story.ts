// Plain-language descriptions of what happened to a request, for the run view.

import { formatStay } from "./format";
import type { RequestDetail } from "./types";

type Reply = { target?: string; flags?: string[]; situation?: string };

// The step a request was in when it failed, as the desk would say it. Raw state names never
// reach the page: a state missing here reads as "working on it".
const FAILED_IN: Record<string, string> = {
  received: "reading the request",
  extracting: "reading the request",
  checking: "running the checks",
  resolving: "looking for other options",
  drafting: "writing the reply",
  ready: "approving the reply",
  approved: "sending the reply",
  rejected: "sending the reply",
};

/** One sentence saying where the request stands, naming who decided it. */
export function outcome(detail: RequestDetail): string {
  const reply = detail.steps.reply as Reply | undefined;
  const approval = detail.approvals.at(-1);
  switch (detail.status) {
    case "sent":
      if (!approval) return "The checks passed it, so it went out without a person.";
      if (approval.action === "reject") {
        return `${approval.staff_name} declined the request, and the pet parent got a polite no.`;
      }
      if (approval.action === "edit_and_approve") return `${approval.staff_name} edited the reply and sent it.`;
      return `${approval.staff_name} approved the reply, and the desk sent it.`;
    case "needs_review":
      return reply?.flags?.length ? `Waiting for you: ${flagText(reply.flags[0])}.` : "Waiting for you.";
    case "failed": {
      const step = FAILED_IN[detail.failed_step ?? ""] ?? "working on it";
      return `Stopped while ${step}. Processing it again resumes from that step.`;
    }
    default:
      return "Working on it.";
  }
}

/** "came through resolving: not_attempted (needs a person: intake: message contains …)" → readable. */
export function flagText(flag: string): string {
  const reason = flag.match(/needs a person: (.*)\)$/)?.[1];
  if (reason) return reason.replace(/^(intake|records): /, "").split("; ")[0];
  if (flag.startsWith("came through resolving: proposed")) return "the resolver proposed other options";
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
