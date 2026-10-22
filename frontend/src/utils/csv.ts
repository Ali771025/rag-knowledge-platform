function escapeCsvValue(value: string): string {
  if (value.includes(",") || value.includes("\n") || value.includes("\"")) {
    return `"${value.replaceAll("\"", "\"\"")}"`;
  }
  return value;
}

export function downloadCsv(params: {
  filename: string;
  headers: string[];
  rows: Array<Array<string | number | boolean | null | undefined>>;
}): void {
  const lines: string[] = [];
  lines.push(params.headers.map((header) => escapeCsvValue(String(header))).join(","));

  for (const row of params.rows) {
    lines.push(
      row
        .map((cell) => {
          if (cell === null || cell === undefined) {
            return "";
          }
          return escapeCsvValue(String(cell));
        })
        .join(",")
    );
  }

  const csv = lines.join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = params.filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
