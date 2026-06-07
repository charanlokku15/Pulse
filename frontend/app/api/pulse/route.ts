import { NextResponse } from "next/server";
import { execSync } from "child_process";

export async function GET() {
  try {
    // Run a Python script to query DuckDB and return JSON
    const result = execSync(
      "cd /Users/charanlokku/pulse && source venv/bin/activate && python ingestion/query_dashboard.py",
      { shell: "/bin/bash" }
    ).toString();

    const data = JSON.parse(result);
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to load data" }, { status: 500 });
  }
}