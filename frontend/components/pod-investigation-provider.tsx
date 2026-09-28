"use client";
import { createContext, useContext, useState, type ReactNode, type Dispatch, type SetStateAction } from "react";
import { usePodInvestigation, type PodSummary } from "@/hooks/use-kubernetes";

type State = {
  selectedPod: PodSummary | null;
  setSelectedPod: Dispatch<SetStateAction<PodSummary | null>>;
  investigationEnabled: boolean;
  setInvestigationEnabled: Dispatch<SetStateAction<boolean>>;
  investigation: ReturnType<typeof usePodInvestigation>;
};
const Context = createContext<State | null>(null);
export function PodInvestigationProvider({children}: {children: ReactNode}) {
  const [selectedPod, setSelectedPod] = useState<PodSummary | null>(null);
  const [investigationEnabled, setInvestigationEnabled] = useState(false);
  const investigation = usePodInvestigation(investigationEnabled ? selectedPod : null);
  return <Context.Provider value={{selectedPod, setSelectedPod, investigationEnabled, setInvestigationEnabled, investigation}}>{children}</Context.Provider>;
}
export function usePodInvestigationState() {
  const state = useContext(Context);
  if (!state) throw new Error("Pod investigation provider is missing.");
  return state;
}
