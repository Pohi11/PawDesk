import { Suspense } from "react";

import { DemoPanel } from "@/components/demo-panel";
import { Loading, PageHeader } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import type { DemoSample } from "@/lib/types";

export default function DemoPage() {
  return (
    <>
      <PageHeader title="Demo">
        Submit a sample request and watch PawDesk handle it live, with real model calls. Each sample
        uses synthetic owners, pets, and certificates, and is processed as of 3 March 2027, the day
        the sample certificates were made for.
      </PageHeader>
      <Suspense fallback={<Loading label="Loading samples…" />}>
        <Samples />
      </Suspense>
    </>
  );
}

async function Samples() {
  const samples = await backendJson<DemoSample[]>("/demo/samples");
  return <DemoPanel samples={samples} />;
}
