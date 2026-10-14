import { notFound } from "next/navigation";
import { Suspense } from "react";

import { RunView } from "@/components/run-view";
import { Loading } from "@/components/ui";
import { BackendError, backendJson } from "@/lib/backend";
import type { RequestDetail } from "@/lib/types";

export default function RunPage({ params }: PageProps<"/requests/[id]">) {
  // params is read inside Suspense, so the page shell can render before the request arrives.
  return (
    <Suspense fallback={<Loading label="Loading run…" />}>
      <Run params={params} />
    </Suspense>
  );
}

async function Run({ params }: Pick<PageProps<"/requests/[id]">, "params">) {
  const { id } = await params;
  let detail: RequestDetail;
  try {
    detail = await backendJson<RequestDetail>(`/requests/${id}`);
  } catch (error) {
    if (error instanceof BackendError && (error.status === 404 || error.status === 422)) {
      notFound();
    }
    throw error;
  }
  return <RunView initial={detail} />;
}
