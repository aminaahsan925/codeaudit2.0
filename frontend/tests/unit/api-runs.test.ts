import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createRun,
  getRun,
  rerunRun,
  CREATE_RUN_TIMEOUT_MS,
} from "@/lib/api";

import { makeRun, RUN_ID } from "./fixtures";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubFetch(impl: (req: Request) => Promise<Response>) {
  const fn = vi.fn(impl);
  vi.stubGlobal("fetch", fn);
  return fn;
}

async function catchError(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (e) {
    expect(e).toBeInstanceOf(ApiError);
    return e as ApiError;
  }
  throw new Error("expected promise to reject");
}

afterEach(() => vi.unstubAllGlobals());

describe("createRun", () => {
  // The multipart body is asserted as raw text: req.formData() cannot
  // parse it in this environment (jsdom File vs. undici FormData realms).
  // In a real browser there is a single realm and the filename survives;
  // here undici serialises the jsdom File with filename "blob", so the
  // tests assert the part exists rather than its exact filename.
  it("posts multipart form data with the project name and repo URL", async () => {
    const fetchMock = stubFetch(async () => json(makeRun({ status: "queued" }), 201));
    const run = await createRun({
      projectName: "pocket-notes",
      repoUrl: "https://github.com/example/pocket-notes",
      liveUrl: "https://pocket-notes.example.app",
    });

    expect(run.status).toBe("queued");
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe("/api/runs");
    expect(req.method).toBe("POST");
    expect(req.headers.get("content-type")).toMatch(/^multipart\/form-data/);
    const body = await req.text();
    expect(body).toContain('name="project_name"');
    expect(body).toContain("pocket-notes");
    expect(body).toContain('name="repo_url"');
    expect(body).toContain("https://github.com/example/pocket-notes");
    expect(body).toContain('name="live_url"');
    expect(body).toContain("https://pocket-notes.example.app");
    expect(body).not.toContain('name="zip_file"');
    expect(body).not.toContain('name="journey_email"');
  });

  it("sends the zip file and journey credentials when given", async () => {
    const fetchMock = stubFetch(async () => json(makeRun({ status: "queued" }), 201));
    const zip = new File(["fake zip bytes"], "app.zip", { type: "application/zip" });
    await createRun({
      projectName: "pocket-notes",
      zipFile: zip,
      journeyEmail: "tester@example.com",
      journeyPassword: "hunter2",
      domainToken: "verify-me",
    });

    const req = fetchMock.mock.calls[0]![0];
    const body = await req.text();
    expect(body).toContain('name="zip_file"');
    expect(body).toContain("filename=");
    expect(body).toContain('name="journey_email"');
    expect(body).toContain("tester@example.com");
    expect(body).toContain('name="journey_password"');
    expect(body).toContain("hunter2");
    expect(body).toContain('name="domain_token"');
    expect(body).toContain("verify-me");
    expect(body).not.toContain('name="repo_url"');
  });

  it("omits empty optional strings instead of sending blanks", async () => {
    const fetchMock = stubFetch(async () => json(makeRun({ status: "queued" }), 201));
    await createRun({
      projectName: "pocket-notes",
      repoUrl: "https://github.com/example/pocket-notes",
      liveUrl: "   ",
      domainToken: "",
    });

    const body = await fetchMock.mock.calls[0]![0].text();
    expect(body).not.toContain('name="live_url"');
    expect(body).not.toContain('name="domain_token"');
  });

  it("surfaces a 429 rate limit as an ApiError", async () => {
    stubFetch(async () =>
      json(
        { error: { code: "bad_request", message: "Too many audits this hour." } },
        429,
      ),
    );
    const err = await catchError(
      createRun({
        projectName: "pocket-notes",
        repoUrl: "https://github.com/example/pocket-notes",
      }),
    );
    expect(err.status).toBe(429);
    expect(err.message).toBe("Too many audits this hour.");
  });

  it("uses the long upload timeout by default", () => {
    expect(CREATE_RUN_TIMEOUT_MS).toBeGreaterThan(10_000);
  });
});

describe("getRun", () => {
  it("fetches the run by id", async () => {
    const fetchMock = stubFetch(async () => json(makeRun()));
    await expect(getRun(RUN_ID)).resolves.toMatchObject({ id: RUN_ID });
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe(`/api/runs/${RUN_ID}`);
    expect(req.method).toBe("GET");
  });

  it("maps a 404 to not_found", async () => {
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Audit run not found." } }, 404),
    );
    const err = await catchError(getRun(RUN_ID));
    expect(err.code).toBe("not_found");
    expect(err.status).toBe(404);
  });
});

describe("rerunRun", () => {
  it("posts without a body when no fresh inputs are given", async () => {
    const fetchMock = stubFetch(async () =>
      json(makeRun({ id: "99999999-9999-4999-8999-999999999999", status: "queued" }), 201),
    );
    const run = await rerunRun(RUN_ID);
    expect(run.status).toBe("queued");
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe(`/api/runs/${RUN_ID}/rerun`);
    expect(req.method).toBe("POST");
  });

  it("sends fresh journey credentials when given", async () => {
    const fetchMock = stubFetch(async () => json(makeRun({ status: "queued" }), 201));
    await rerunRun(RUN_ID, {
      journey_email: "tester@example.com",
      journey_password: "hunter2",
      domain_token: null,
    });
    const req = fetchMock.mock.calls[0]![0];
    expect(await req.json()).toEqual({
      journey_email: "tester@example.com",
      journey_password: "hunter2",
      domain_token: null,
    });
  });
});
