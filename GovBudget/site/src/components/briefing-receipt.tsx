"use client";

import { useContext } from "react";
import { CitationPanelContext } from "@/components/cite";

export function BriefingReceipt({ factId }: { factId: string }) {
  const { openPanel } = useContext(CitationPanelContext);
  return <button type="button" className="underline" onClick={() => openPanel(factId)}>Read source passage</button>;
}
