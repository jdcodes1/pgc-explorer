/**
 * Load pre-computed JSON snapshots from public/data/.
 */

export interface ManhattanSNP {
  snp: string;
  chr: number;
  bp: number;
  neglog10p: number;
  beta: number;
}

export interface ManhattanData {
  disorder: string;
  snps: ManhattanSNP[];
  count: number;
}

export interface CorrelationMatrix {
  labels: string[];
  values: number[][];
  overlap_counts?: number[][];
}

export interface NetworkNode {
  id: string;
  sigLoci: number;
  color: string;
}

export interface NetworkLink {
  source: string;
  target: string;
  weight: number;
}

export interface NetworkGraph {
  nodes: NetworkNode[];
  links: NetworkLink[];
}

export interface DisorderMeta {
  name: string;
  snpCount: number;
  color: string;
}

export interface Metadata {
  disorders: DisorderMeta[];
  totalSnps: number;
}

export async function loadCorrelationMatrix(): Promise<CorrelationMatrix> {
  const res = await fetch("/data/correlation_matrix.json");
  return res.json();
}

export async function loadManhattanData(disorder: string): Promise<ManhattanData> {
  const res = await fetch(`/data/manhattan/${disorder}.json`);
  return res.json();
}

export async function loadNetworkGraph(): Promise<NetworkGraph> {
  const res = await fetch("/data/network_graph.json");
  return res.json();
}

export async function loadMetadata(): Promise<Metadata> {
  const res = await fetch("/data/metadata.json");
  return res.json();
}
