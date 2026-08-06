"""`is_non_implementation_file` — which files cannot implement a requirement.

Why this predicate exists
-------------------------
Mind Map judges whether production code implements a requirement. A file that compiles to
nothing, or that only describes shapes and settings, can never be the answer — yet a real
run cited `src/types/*.types.ts` as evidence, and a real indexing pass spent 42,704 bytes
of a finite code budget on `prisma/seed.ts`. Correctness is the argument: an
`interface CreateEventRequest` names the shape of a request perfectly and says nothing
about whether any code handles one. Budget is a side effect, and a small one (~6-7%).

The fixtures below are verbatim excerpts from the repository where the false positives
were actually observed (nearu-backend), not invented examples, because the failures this
guards against were all cases where a plausible-looking rule met a real file and lost.

The two things this file is really defending
--------------------------------------------
1. Nothing real gets dropped. A dropped file is INVISIBLE: it can no longer be cited, so a
   requirement that genuinely is implemented silently reads as uncovered, and there is no
   error anywhere to trace it back to. MUST_NOT_DROP is therefore the load-bearing test in
   this module — if it and only it survived, that would still be worth having.
2. `is_test_file` keeps its old meaning. It is used elsewhere to count developer-authored
   tests for the automation-coverage percentage. Folding type declarations and seed data
   into it — the obvious shortcut — would report `activity.types.ts` as a test and quietly
   inflate that number, which is why these are two predicates and not one.
"""
import coverage as cov

# --------------------------------------------------------------------------- fixtures
# Verbatim heads of real files. Kept exact (including the commented-out block in phone.ts,
# which is the reason the content rule strips comments before looking for runtime code).

ACTIVITY_TYPES_TS = """\
export interface ActivityCategory {
  id: string;
  name: string;
  slug: string;
  icon: string;
  description?: string;
  sortOrder: number;
  isActive: boolean;
}

export interface Activity {
  id: string;
  categoryId: string;
  code: string;
}
"""

EVENT_TYPES_TS = """\
import { EventStatus } from '@prisma/client';

export interface CreateEventRequest {
  title: string;
  description?: string;
  activityId: string;           // UUID from Activity table

  // Location
  locationLabel?: string;
  latitude: number;
  longitude: number;
}
"""

QUEUE_TYPES_TS = """\
/**
 * Job data for ending an event
 */
export interface EndEventJobData {
  eventId: string;
  endTime: Date;
}

/**
 * Job data for archiving an event
 */
export interface ArchiveEventJobData {
  eventId: string;
  deleteAfter: Date;
}
"""

RATING_TYPES_TS = """\
// ================================================================
// rating.types.ts — Shared TypeScript interfaces for rating system
// ================================================================

// AuthRequest lives in auth.middleware.ts — import from there:
// import { AuthRequest } from "../middlewares/auth.middleware";

export interface RaterUser {
  id: string;
  trustScore: number;
}
"""

BAD_WORDS_D_TS = """\
declare module "bad-words" {
  class Filter {
    constructor(options?: {
      placeHolder?: string;
      regex?: RegExp;
    });
    addWords(...words: string[]): void;
    clean(text: string): string;
    isProfane(text: string): boolean;
  }
  export { Filter };
}
"""

# --- files that MUST survive ------------------------------------------------------------

ENV_TS = """\
import "dotenv/config";

function required(name: string, value?: string) {
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

export const env = {
  PORT: Number(process.env.PORT || 4000),
  DATABASE_URL: required("DATABASE_URL", process.env.DATABASE_URL),
};
"""

EVENT_CONSTANTS_TS = """\
/**
 * EVENT TIMING CONSTANTS
 */

// Visibility rules
export const VISIBILITY_BEFORE_START_HOURS = 1;

// Creation rules
export const MAX_HOURS_IN_ADVANCE = 24;
export const MIN_DURATION_MINUTES = 30;
export const MAX_DURATION_MINUTES = 480; // 8 hours

// Lifecycle rules
export const RATING_DEADLINE_HOURS = 24;
"""

JWT_SERVICE_TS = """\
import * as jwt from "jsonwebtoken";
import type { Secret, SignOptions } from "jsonwebtoken";
import { env } from "../config/env";

export function signAccessToken(payload: { userId: string }) {
  const secret: Secret = env.JWT_SECRET as Secret;

  const options: SignOptions = {
    expiresIn: env.JWT_EXPIRES_IN as any,
  };

  return jwt.sign(payload, secret, options);
}
"""

# Verbatim, comment block included: everything runtime-looking in the first 17 lines is
# commented out. A content rule that did not strip comments would still keep this file, so
# this fixture proves the rule works for the right reason, not by accident.
PHONE_TS = """\
// export function normalizePhone(input: string) {
//   let phone = input.replace(/\\D/g, "");

//   if (phone.length === 10) {
//     return `+91${phone}`;
//   }

//   throw new Error("Invalid phone number");
// }
import { parsePhoneNumberFromString } from "libphonenumber-js";

export function normalizePhone(input: string) {
  const phone = parsePhoneNumberFromString(input, "IN");

  if (!phone || !phone.isValid()) {
    throw new Error("Invalid phone number");
  }

  return phone.number; // always E.164
}
"""

AUTH_CONTROLLER_TS = """\
import { Request, Response } from "express";
import { normalizePhone } from "../utils/phone";

export async function sendOtp(req: Request, res: Response) {
  const phone = normalizePhone(req.body.phone);
  const otp = generateOtp();
  await redis.set(`otp:${phone}`, otp, "EX", 300);
  return res.json({ ok: true });
}
"""

SEED_TS = """\
import "dotenv/config";
import { PrismaClient } from "@prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import { Pool } from "pg";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });
"""

VITEST_CONFIG_TS = """\
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    coverage: { provider: 'v8', reporter: ['text', 'lcov'] },
  },
})
"""


# The set that must NEVER be dropped, with real text so the content rule is exercised too.
# Every entry is a file a rationale could legitimately cite as proof of implementation:
# a controller, a token signer, a validator, an env contract that throws, named constants.
MUST_NOT_DROP = [
    ("backend/src/controllers/auth.controller.ts", AUTH_CONTROLLER_TS),
    ("backend/src/services/jwt.service.ts", JWT_SERVICE_TS),
    ("backend/src/utils/phone.ts", PHONE_TS),
    ("backend/src/config/env.ts", ENV_TS),
    ("backend/src/constants/event.constants.ts", EVENT_CONSTANTS_TS),
]

# Type declarations: no runtime output, so no possible evidence of behaviour.
DECLARATION_ONLY = [
    ("backend/src/types/activity.types.ts", ACTIVITY_TYPES_TS),
    ("backend/src/types/event.types.ts", EVENT_TYPES_TS),
    ("backend/src/types/queue.types.ts", QUEUE_TYPES_TS),
    ("backend/src/services/rating/rating.types.ts", RATING_TYPES_TS),
]

# Caught by path alone — no text needed, which matters because the indexer's gate and the
# citation check do not always have the body to hand.
DROPPED_BY_PATH = [
    "backend/src/types/bad-words.d.ts",
    "backend/vitest.config.ts",
    "backend/prisma/seed.ts",
    "backend/prisma/migrations/0_baseline/migration.sql",
    "backend/prisma/migrations/20240101_init/migration.sql",
    "backend/src/__mocks__/redis.ts",
    "backend/tests/fixtures/users.ts",
    "app/stubs/thing.pyi",
]


class TestNothingRealIsDropped:
    """The failure that cannot be detected in production: real code silently excluded."""

    def test_must_not_drop_list_survives_with_text(self):
        for path, text in MUST_NOT_DROP:
            assert cov.is_non_implementation_file(path, text) is False, (
                f"{path} would be excluded from indexing and could no longer be cited — "
                "a requirement it implements would read as uncovered with no trace why")

    def test_must_not_drop_list_survives_on_path_alone(self):
        for path, _text in MUST_NOT_DROP:
            assert cov.is_non_implementation_file(path) is False, path

    def test_constants_and_config_directories_are_not_path_excluded(self):
        # Deliberately NOT path rules: `export const MAX_DURATION_MINUTES = 480` is a
        # runtime value a rationale may cite, and plenty of projects put real helpers in
        # config/. The content rule decides these, and decides to keep them.
        for path in ("backend/src/constants/event.constants.ts",
                     "backend/src/config/env.ts",
                     "backend/src/config/redis.ts"):
            assert cov.NON_IMPL_PATH_RE.search(path) is None, path

    def test_types_directory_is_not_blanket_excluded_by_path(self):
        # The tempting rule. Rejected: a runtime helper living in types/ would vanish.
        # Only its CONTENT may condemn it.
        assert cov.NON_IMPL_PATH_RE.search(
            "backend/src/types/activity.types.ts") is None
        assert cov.is_non_implementation_file(
            "backend/src/types/activity.types.ts") is False   # path alone: keep
        assert cov.is_non_implementation_file(
            "backend/src/types/activity.types.ts", ACTIVITY_TYPES_TS) is True

    def test_a_runtime_helper_in_types_dir_survives(self):
        helper = ("export function isActivityCode(v: unknown): boolean {\n"
                  "  return typeof v === 'string' && v.length > 0;\n}\n")
        assert cov.is_non_implementation_file(
            "backend/src/types/guards.types.ts", helper) is False

    def test_unknown_or_empty_text_keeps_the_file(self):
        # Unknown must mean "keep". Anything else turns an unmodelled language into an
        # invisible exclusion.
        for text in ("", "   \n\n", "package main\n\nimport \"fmt\"\n",
                     "export { sendOtp } from './auth.controller';\n"):
            assert cov.is_non_implementation_file("src/thing.ts", text) is False, repr(text)

    def test_none_and_empty_path_are_safe(self):
        assert cov.is_non_implementation_file(None) is False
        assert cov.is_non_implementation_file("") is False
        assert cov.is_non_implementation_file("", None) is False


class TestDeclarationOnlyFilesAreDropped:
    def test_declaration_only_fixtures_are_excluded(self):
        for path, text in DECLARATION_ONLY:
            assert cov.is_non_implementation_file(path, text) is True, (
                f"{path} compiles to no JavaScript, so it cannot implement anything, "
                "yet it would still be offered as citable evidence")

    def test_comments_are_stripped_before_looking_for_runtime_code(self):
        # rating.types.ts opens with commented-out import lines; queue.types.ts with a
        # JSDoc block. Neither is runtime code, and neither may rescue the file.
        assert cov._is_declaration_only(RATING_TYPES_TS) is True
        assert cov._is_declaration_only(QUEUE_TYPES_TS) is True

    def test_a_commented_out_implementation_does_not_rescue_a_type_file(self):
        text = ("// export function normalize(x: string) { return x.trim(); }\n"
                "export interface Normalized { value: string }\n")
        assert cov._is_declaration_only(text) is True

    def test_but_real_code_after_a_commented_out_block_does_rescue_it(self):
        # The inverse, from a real file: phone.ts is 17 lines of dead comment followed by
        # a working implementation. Stripping comments must not strip the live code with it.
        assert cov._is_declaration_only(PHONE_TS) is False

    def test_value_constructs_always_win_over_type_declarations(self):
        mixed = ("export interface Options { retries: number }\n"
                 "export const DEFAULT_OPTIONS: Options = { retries: 3 };\n")
        assert cov._is_declaration_only(mixed) is False

    def test_path_rules_catch_what_content_cannot(self):
        # bad-words.d.ts declares a `class`, so the content rule votes to keep it — being
        # a .d.ts is what makes it inert, and only the path knows that. Belt and braces.
        assert cov._is_declaration_only(BAD_WORDS_D_TS) is False
        assert cov.is_non_implementation_file(
            "backend/src/types/bad-words.d.ts", BAD_WORDS_D_TS) is True


class TestPathRules:
    def test_dropped_by_path_needs_no_text(self):
        for path in DROPPED_BY_PATH:
            assert cov.is_non_implementation_file(path) is True, path

    def test_named_build_tool_configs_are_excluded(self):
        for path in ("vitest.config.ts", "backend/tailwind.config.js",
                     "app/next.config.mjs", "prisma.config.ts",
                     "packages/api/jest.config.cjs", "playwright.config.ts"):
            assert cov.is_non_implementation_file(path) is True, path

    def test_config_rule_is_an_allowlist_not_a_glob(self):
        """Regression: a `*.config.ts` glob dropped real application code.

        Both files below are from the repo where this was measured. firebase.config.ts
        throws when credentials are missing and exports the `messaging` client;
        queue.config.ts holds the job retry count and backoff policy. A test case about
        push delivery or job retries would be judged against exactly these, so a glob that
        swallowed them would report those cases uncovered with nothing to point at.
        """
        for path in ("backend/src/config/firebase.config.ts",
                     "backend/src/config/queue.config.ts",
                     "backend/src/config/database.config.ts",
                     "backend/src/services/config.service.ts",
                     "backend/src/configure.ts",
                     "backend/src/config/env.ts",
                     "backend/src/reconfigure.ts"):
            assert cov.is_non_implementation_file(path) is False, path

    def test_application_config_survives_with_its_real_text(self):
        firebase = (
            'import admin from "firebase-admin";\n'
            'if (process.env.FIREBASE_SERVICE_ACCOUNT) {\n'
            '  serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);\n'
            '} else {\n'
            '  throw new Error("Firebase credentials not found.");\n'
            '}\n'
            'export const messaging = admin.messaging();\n')
        queue = ('export const JOB_CONFIG = {\n'
                 '  attempts: 3,\n'
                 '  backoff: { type: "exponential" as const, delay: 5000 },\n'
                 '} as const;\n')
        assert cov.is_non_implementation_file(
            "backend/src/config/firebase.config.ts", firebase) is False
        assert cov.is_non_implementation_file(
            "backend/src/config/queue.config.ts", queue) is False

    def test_seed_rule_targets_the_script_not_anything_seedish(self):
        assert cov.is_non_implementation_file("backend/prisma/seed.ts") is True
        assert cov.is_non_implementation_file("backend/src/seeds/activities.ts") is True
        # A service that happens to seed is real code.
        assert cov.is_non_implementation_file("backend/src/services/seeder.service.ts") is False
        assert cov.is_non_implementation_file("backend/src/utils/seedRandom.ts") is False

    def test_migrations_and_sql_are_excluded(self):
        assert cov.is_non_implementation_file("prisma/migrations/0_baseline/migration.sql") is True
        assert cov.is_non_implementation_file("db/schema.sql") is True
        # ...but a hand-written migration RUNNER is implementation.
        assert cov.is_non_implementation_file("src/db/migrator.ts") is False

    def test_it_is_a_strict_superset_of_is_test_file(self):
        for path in ("backend/src/wardon-specs/login-flow/bus-1-no-name-join.ts",
                     "backend/tests/login-flow/api/api-2-verify-otp.test.ts",
                     "backend/specs/a.ts",
                     "src/vendor.test.ts",
                     "tests/feedback.test.ts"):
            assert cov.is_test_file(path) is True, path
            assert cov.is_non_implementation_file(path) is True, path


class TestIsTestFileSemanticsUnchanged:
    """is_test_file feeds the automation-coverage percentage. It must not have moved.

    If these ever start passing under the wider meaning, the reported count of
    developer-authored tests has silently absorbed type declarations and seed data.
    """

    NOT_TESTS_BUT_NON_IMPL = [
        "backend/src/types/bad-words.d.ts",
        "backend/vitest.config.ts",
        "backend/prisma/seed.ts",
        "backend/prisma/migrations/0_baseline/migration.sql",
        "app/stubs/thing.pyi",
    ]

    def test_new_exclusions_are_not_reported_as_tests(self):
        for path in self.NOT_TESTS_BUT_NON_IMPL:
            assert cov.is_test_file(path) is False, (
                f"{path} is now counted as a developer-authored test — automation "
                "coverage would be inflated by files nobody wrote as tests")
            assert cov.is_non_implementation_file(path) is True, path

    def test_declaration_only_content_never_makes_a_file_a_test(self):
        for path, text in DECLARATION_ONLY:
            assert cov.is_test_file(path) is False, path

    def test_real_tests_are_still_tests(self):
        for path in ("tests/feedback.test.ts", "src/vendor.test.ts",
                     "backend/tests/login-flow/api/auth.api.test.ts",
                     "app/tests/test_thing.py", "src/UserServiceTest.java"):
            assert cov.is_test_file(path) is True, path

    def test_is_test_file_still_takes_one_argument(self):
        # Signature is part of the contract: callers elsewhere pass a path and nothing else.
        import inspect
        params = list(inspect.signature(cov.is_test_file).parameters)
        assert params == ["path"], params


class TestCitationEligibility:
    """Citing an inert file must not be able to establish coverage."""

    def _idx(self, path, text):
        return cov.citation_index([{"repo": "r", "path": path, "text": text}])

    def test_citing_a_type_declaration_yields_uncovered(self):
        path = "backend/src/types/event.types.ts"
        idx = self._idx(path, EVENT_TYPES_TS)
        v = cov._ground_verdict(
            "covered", "the `CreateEventRequest` shape enforces latitude and longitude",
            ["r:" + path], idx, model_confidence=1.0)
        assert v["status"] == "uncovered"
        assert v["files_ineligible"] == ["r:" + path]
        assert v["files"] == []
        assert v["needs_review"] is True
        assert v["confidence"] <= 0.2

    def test_citing_a_d_ts_file_yields_uncovered(self):
        path = "backend/src/types/bad-words.d.ts"
        idx = self._idx(path, BAD_WORDS_D_TS)
        v = cov._ground_verdict("covered", "profanity is filtered by `Filter`",
                                ["r:" + path], idx, model_confidence=1.0)
        assert v["status"] == "uncovered"
        assert v["files_ineligible"] == ["r:" + path]

    def test_citing_seed_data_yields_uncovered(self):
        path = "backend/prisma/seed.ts"
        idx = self._idx(path, SEED_TS)
        v = cov._ground_verdict("covered", "the activity categories are created there",
                                ["r:" + path], idx, model_confidence=1.0)
        assert v["status"] == "uncovered"
        assert v["files_ineligible"] == ["r:" + path]

    def test_citing_tool_config_yields_uncovered(self):
        path = "backend/vitest.config.ts"
        idx = self._idx(path, VITEST_CONFIG_TS)
        v = cov._ground_verdict("covered", "`defineConfig` wires the test environment",
                                ["r:" + path], idx, model_confidence=1.0)
        assert v["status"] == "uncovered"
        assert v["files_ineligible"] == ["r:" + path]

    def test_a_real_implementation_citation_is_still_accepted(self):
        # The control. Without it every assertion above could be satisfied by a predicate
        # that rejects everything.
        path = "backend/src/controllers/auth.controller.ts"
        idx = self._idx(path, AUTH_CONTROLLER_TS)
        v = cov._ground_verdict("covered", "`sendOtp` normalises the phone and stores the otp",
                                ["r:" + path], idx, model_confidence=0.9)
        assert v["status"] == "covered"
        assert v["files"] == ["r:" + path]
        assert v["files_ineligible"] == []
        assert v["grounding"]["symbols_supported"] is True
        assert v["needs_review"] is False

    def test_constants_remain_usable_as_evidence(self):
        path = "backend/src/constants/event.constants.ts"
        idx = self._idx(path, EVENT_CONSTANTS_TS)
        v = cov._ground_verdict(
            "covered", "the 24h limit is `MAX_HOURS_IN_ADVANCE`", ["r:" + path], idx,
            model_confidence=0.9)
        assert v["status"] == "covered"
        assert v["files"] == ["r:" + path]

    def test_a_mixed_citation_keeps_the_eligible_file(self):
        # One good file, one type declaration: the verdict stands on the good one, and the
        # ineligible citation is still reported rather than quietly dropped.
        good = "backend/src/controllers/auth.controller.ts"
        bad = "backend/src/types/event.types.ts"
        idx = cov.citation_index([
            {"repo": "r", "path": good, "text": AUTH_CONTROLLER_TS},
            {"repo": "r", "path": bad, "text": EVENT_TYPES_TS},
        ])
        v = cov._ground_verdict("covered", "`sendOtp` handles it", ["r:" + good, "r:" + bad],
                                idx, model_confidence=0.9)
        assert v["status"] == "covered"
        assert v["files"] == ["r:" + good]
        assert v["files_ineligible"] == ["r:" + bad]
        assert v["grounding"]["citations_ineligible"] == 1

    def test_ineligible_note_no_longer_claims_the_file_was_a_test(self):
        # The wording is user-facing: reporting `event.types.ts` as "test/spec code" would
        # send someone looking for a test that does not exist.
        path = "backend/src/types/event.types.ts"
        idx = self._idx(path, EVENT_TYPES_TS)
        v = cov._ground_verdict("covered", "the request shape covers it", ["r:" + path],
                                idx, model_confidence=1.0)
        note = " ".join(v["grounding"]["notes"]).lower()
        assert "cannot implement behaviour" in note
