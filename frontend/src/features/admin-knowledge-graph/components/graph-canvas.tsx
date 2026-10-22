import { useMemo } from "react";
import type { KnowledgeGraphEdge, KnowledgeGraphNode } from "@/types/admin";

interface GraphCanvasProps {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  selectedNodeId?: string;
  onSelectNode: (nodeId: string) => void;
}

const typeColorMap: Record<string, string> = {
  person: "#ef4444",
  organization: "#3b82f6",
  concept: "#22c55e",
  technology: "#f97316",
  location: "#14b8a6",
  other: "#64748b"
};

interface PositionedNode {
  node: KnowledgeGraphNode;
  x: number;
  y: number;
}

export function GraphCanvas({ nodes, edges, selectedNodeId, onSelectNode }: GraphCanvasProps) {
  const width = 920;
  const height = 420;

  const positionedNodes = useMemo<PositionedNode[]>(() => {
    if (nodes.length === 0) return [];

    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.36;

    return nodes.map((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(1, nodes.length);
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      return { node, x, y };
    });
  }, [nodes]);

  const positionLookup = useMemo(() => {
    const lookup = new Map<string, PositionedNode>();
    for (const item of positionedNodes) {
      lookup.set(item.node.id, item);
    }
    return lookup;
  }, [positionedNodes]);

  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Graph Canvas</h2>
      <p className="mt-1 text-sm text-muted-foreground">Interactive SVG rendering for filtered graph nodes and edges.</p>

      <div className="mt-3 overflow-auto rounded-lg border border-border bg-muted/30">
        {nodes.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">No graph data for current filters.</p>
        ) : (
          <svg viewBox={`0 0 ${width} ${height}`} className="h-[420px] w-full min-w-[640px]">
            {edges.map((edge) => {
              const source = positionLookup.get(edge.source);
              const target = positionLookup.get(edge.target);
              if (!source || !target) return null;
              return (
                <g key={edge.id}>
                  <line
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    stroke="#94a3b8"
                    strokeWidth={1.5}
                    opacity={0.65}
                  />
                  <text
                    x={(source.x + target.x) / 2}
                    y={(source.y + target.y) / 2}
                    textAnchor="middle"
                    fontSize="11"
                    fill="#334155"
                  >
                    {edge.relation}
                  </text>
                </g>
              );
            })}

            {positionedNodes.map(({ node, x, y }) => {
              const isSelected = node.id === selectedNodeId;
              return (
                <g key={node.id} onClick={() => onSelectNode(node.id)} className="cursor-pointer">
                  <circle
                    cx={x}
                    cy={y}
                    r={isSelected ? 18 : 14}
                    fill={typeColorMap[node.type] ?? typeColorMap.other}
                    stroke={isSelected ? "#0f172a" : "#ffffff"}
                    strokeWidth={isSelected ? 3 : 2}
                  />
                  <text x={x} y={y + 28} textAnchor="middle" fontSize="12" fill="#0f172a">
                    {node.label.slice(0, 24)}
                  </text>
                </g>
              );
            })}
          </svg>
        )}
      </div>
    </section>
  );
}
