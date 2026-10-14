import { Suspense } from "react";

import { DemoPanel } from "@/components/demo-panel";
import { Loading, PageTitle } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import type { DemoSample } from "@/lib/types";

export default function DemoPage() {
  return (
    <>
      <PageTitle title="Try a request">
        Send a sample request from one of the synthetic pet parents and watch the desk handle it live,
        with real model calls. Samples are handled as of March 3, 2027, the day their certificates were
        made for.
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
