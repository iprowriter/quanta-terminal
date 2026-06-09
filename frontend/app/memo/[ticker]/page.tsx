import MemoViewer from "@/components/memo/MemoViewer";

interface Props {
  params: { ticker: string };
}

export default function MemoPage({ params }: Props) {
  return <MemoViewer ticker={params.ticker.toUpperCase()} />;
}
