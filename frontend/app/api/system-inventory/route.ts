import { readFile } from "node:fs/promises";

import { NextResponse } from "next/server";

export async function GET() {
  try {
    const markdown = await readFile("/docs/system-inventory-audit.md", "utf-8");
    return NextResponse.json({ status: "ok", markdown });
  } catch (error) {
    return NextResponse.json(
      {
        status: "error",
        markdown: "",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    );
  }
}
