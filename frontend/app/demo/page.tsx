import { Suspense } from "react";

import { DemoPanel } from "@/components/demo-panel";
import { Loading, PageTitle } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import type { DemoSample } from "@/lib/types";

export default function DemoPage() {
  return (
    <>
      <PageTitle title="Try a request">
        Make up a request for one of the synthetic pet parents or pick a sample, then watch each
        step run with real model calls. The desk treats today as March 3, 2027, so the vaccine
        cards&apos; dates line up with the stays.
      </PageTitle>
      <Suspense fallback={<Loading label="Loading samples" />}>
        <Samples />
      </Suspense>
    </>
  );
}

async function Samples() {
  const samples = await backendJson<DemoSample[]>("/demo/samples");
  return <DemoPanel samples={samples} />;
}
