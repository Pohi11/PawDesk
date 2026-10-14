import { Suspense } from "react";

import { ReviewQueue } from "@/components/review-card";
import { Loading, PageTitle } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import type { ReviewItem } from "@/lib/types";

export default function ReviewsPage() {
  return (
    <>
      <PageTitle title="Review queue">
        Each request here stopped for a reason a person has to judge. Read the reason, then send the
        reply as written, edit it first, or decline.
      </PageTitle>
      <Suspense fallback={<Loading label="Loading the queue" />}>
        <Queue />
      </Suspense>
    </>
  );
}

async function Queue() {
  const items = await backendJson<ReviewItem[]>("/reviews");
  if (items.length === 0) {
    return <p className="text-lg text-muted">Nothing is waiting. Requests the checks can&apos;t decide show up here.</p>;
  }
  return <ReviewQueue items={items} />;
}
