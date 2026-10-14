import { Suspense } from "react";

import { ReviewCard } from "@/components/review-card";
import { Loading, PageHeader } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import type { ReviewItem } from "@/lib/types";

export default function ReviewsPage() {
  return (
    <>
      <PageHeader title="Review queue">
        Requests that need a person, with the reasons code flagged them. Approve the draft, edit it
        before it goes out, or reject with a reason (kept internal; the customer gets a polite
        decline).
      </PageHeader>
      <Suspense fallback={<Loading label="Loading the queue…" />}>
        <Queue />
      </Suspense>
    </>
  );
}

async function Queue() {
  const items = await backendJson<ReviewItem[]>("/reviews");
  if (items.length === 0) {
    return <p className="text-sm text-zinc-500">Nothing is waiting for review.</p>;
  }
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <ReviewCard key={item.id} item={item} />
      ))}
    </div>
  );
}
