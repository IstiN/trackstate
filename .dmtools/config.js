/**
 * TrackState project configuration for DMTools agents.
 *
 * The shared agents submodule resolves this file from ../.dmtools/config.js.
 * Jira project values are wired to the TrackState Jira project.
 */
const GOAL_INSTRUCTIONS = './.dmtools/instructions/goal/goal.md';
const DESIGN_REFERENCE = './.dmtools/instructions/goal/DESIGN.md';
const SETUP_REPO_INSTRUCTIONS = './.dmtools/instructions/product/trackstate_setup_repo.md';
const TRACKSTATE_TEST_AUTOMATION_RULES = './.dmtools/instructions/agents/test_automation_hardening.md';
const TRACKSTATE_BUG_TEST_AUTOMATION_SCOPE = './.dmtools/instructions/agents/bug_test_automation_scope.md';
const TRACKSTATE_TEST_REVIEW_CHECKLIST = './.dmtools/instructions/agents/test_automation_review_checklist.md';
const TRACKSTATE_FLUTTER_RULES = './.dmtools/instructions/agents/flutter_development_rules.md';
const TRACKSTATE_WEB_FOCUS_RULES = './.dmtools/instructions/agents/flutter_web_focus_keyboard_rules.md';
const BUG_DEV_ANTIPATTERNS = './.dmtools/prompts/bug_dev_antipatterns.md';
const TEST_AUTOMATION_ANTIPATTERNS = './.dmtools/prompts/test_automation_antipatterns.md';
const TRACKSTATE_SETUP_SUBMODULES = [
    { path: 'trackstate-setup', branch: 'main', tagPrefix: 'stable' }
];
const POST_ACTION_FEEDBACK = {
    postAction: {
        enabled: true,
        maxAttempts: 2
    }
};
const FLUTTER_FEEDBACK = {
    postAction: {
        enabled: true,
        maxAttempts: 2
    },
    qualityGates: {
        enabled: true,
        gates: [
            { name: 'flutter-analyze', command: 'flutter analyze', maxAttempts: 2 },
            { name: 'flutter-test', command: 'flutter test --coverage', maxAttempts: 2 },
            { name: 'accessibility-build', command: 'bash tool/run_if_accessibility_needed.sh \"flutter build web --release --base-href / --pwa-strategy=none --dart-define TRACKSTATE_USE_DEMO_REPOSITORY=true --dart-define TRACKSTATE_REPOSITORY=IstiN/trackstate-setup --dart-define TRACKSTATE_SOURCE_REF=main --dart-define TRACKSTATE_DATA_REF=main\"', maxAttempts: 1 },
            { name: 'accessibility-axe', command: 'bash tool/run_if_accessibility_needed.sh \"npm run test:a11y\"', maxAttempts: 1 },
            { name: 'accessibility-log-validation', command: 'bash tool/run_if_accessibility_needed.sh \"node testing/accessibility/log_validation.node.test.js\"', maxAttempts: 1 }
        ]
    },
    policyGates: {
        enabled: true,
        gates: [
            { name: 'theme-token-lint', command: 'dart run tool/check_theme_tokens.dart', maxAttempts: 2 },
            { name: 'web-safety-lint', command: 'dart run tool/check_web_safety.dart', maxAttempts: 2 },
            { name: 'file-line-limit-lint', command: 'dart run tool/check_file_line_limits.dart', maxAttempts: 2 },
            { name: 'code-duplication-lint', command: 'npx jscpd@4 lib/ --min-lines 5 --min-tokens 50 --ignore "**/*.g.dart,**/*.freezed.dart,lib/l10n/generated/**,lib/**/*.gr.dart" --threshold 1', maxAttempts: 2 }
        ]
    }
};

module.exports = {
    defaultTracker: 'jira',

    globalCliPrompts: [
        './agents/prompts/codegraph_tools.md'
    ],

    // Keep codegraph_tools only in globalCliPrompts; adding it to additionalInstructions
    // as well duplicates the mermaid diagram in every agent prompt.
    globalAdditionalInstructions: [],
    // SM parallelism: run only one AI teammate workflow at a time to keep PR review/rework first.
    smMaxWorkflows: 1,
    smRules: [
    {
        "description": "In Testing Stories (pr_approved or already-merged test PR) \u2192 merge test automation PR",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('In Testing') AND labels in ('pr_approved','test_pr_merged') AND labels NOT IN ('test_pr_finalized') ORDER BY created ASC",
        "configFile": "agents/story_test_automation_merge.json",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "In Testing Bugs (pr_approved or already-merged test PR) \u2192 merge test automation PR",
        "jql": "project = {jiraProject} AND issuetype in ('Bug') AND status in ('In Testing') AND labels in ('pr_approved','test_pr_merged') AND labels NOT IN ('test_pr_finalized') ORDER BY created ASC",
        "configFile": "agents/bug_test_automation_merge.json",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "Test Cases with dirty open PR \u2192 move to In Rework",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('In Review - Passed', 'In Review - Failed', 'Passed', 'Failed', 'Pull Request Review', 'Merged') AND labels NOT IN ('sm_test_rework_triggered') AND updated >= -2d ORDER BY created ASC",
        "configFile": "agents/recover_dirty_review_test_case.json",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "In Rework Test Cases \u2192 trigger pr_test_automation_rework",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('In Rework') ORDER BY created ASC",
        "configFile": "agents/pr_test_automation_rework.json",
        "skipIfLabel": "sm_test_rework_triggered",
        "addLabel": "sm_test_rework_triggered",
        "enabled": true
    },
    {
        "description": "In Testing Stories (test_pr_rework_needed) \u2192 rework test automation",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('In Testing') AND labels = 'test_pr_rework_needed' ORDER BY created ASC",
        "configFile": "agents/story_test_automation_rework.json",
        "skipIfLabel": "sm_story_test_rework_triggered",
        "addLabel": "sm_story_test_rework_triggered",
        "enabled": true
    },
    {
        "description": "In Testing Bugs (test_pr_rework_needed) \u2192 rework test automation",
        "jql": "project = {jiraProject} AND issuetype in ('Bug') AND status in ('In Testing') AND labels = 'test_pr_rework_needed' ORDER BY created ASC",
        "configFile": "agents/bug_test_automation_rework.json",
        "skipIfLabel": "sm_bug_test_rework_triggered",
        "addLabel": "sm_bug_test_rework_triggered",
        "enabled": true
    },
    {
        "description": "In Testing Stories with open test-automation PR \u2192 review",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('In Testing') AND (labels is EMPTY OR labels NOT IN ('pr_approved','test_pr_rework_needed','test_pr_merged','test_pr_finalized')) ORDER BY created ASC",
        "configFile": "agents/pr_story_test_automation_review.json",
        "skipIfLabel": "sm_story_test_review_triggered",
        "addLabel": "sm_story_test_review_triggered",
        "enabled": true
    },
    {
        "description": "In Testing Bugs with open test-automation PR \u2192 review",
        "jql": "project = {jiraProject} AND issuetype in ('Bug') AND status in ('In Testing') AND (labels is EMPTY OR labels NOT IN ('pr_approved','test_pr_rework_needed','test_pr_merged','test_pr_finalized')) ORDER BY created ASC",
        "configFile": "agents/pr_bug_test_automation_review.json",
        "skipIfLabel": "sm_bug_test_review_triggered",
        "addLabel": "sm_bug_test_review_triggered",
        "enabled": true
    },
    {
        "description": "In Review Stories & Bugs \u2192 trigger pr_review",
        "jql": "project = {jiraProject} AND issuetype in ('Story', 'Bug') AND status in ('In Review') AND (labels is EMPTY OR labels NOT IN ('pr_approved'))",
        "configFile": "agents/pr_review.json",
        "skipIfLabel": "sm_story_review_triggered",
        "addLabel": "sm_story_review_triggered",
        "enabled": true
    },
    {
        "description": "In Rework Stories & Bugs \u2192 trigger pr_rework",
        "jql": "project = {jiraProject} AND issuetype in ('Story', 'Bug') AND status in ('In Rework')",
        "configFile": "agents/pr_rework.json",
        "skipIfLabel": "sm_story_rework_triggered",
        "addLabel": "sm_story_rework_triggered",
        "enabled": true
    },
    {
        "description": "In Review Test Cases \u2192 trigger pr_test_automation_review",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('In Review - Passed', 'In Review - Failed') AND (labels is EMPTY OR labels NOT IN ('pr_approved'))",
        "configFile": "agents/pr_test_automation_review.json",
        "skipIfLabel": "sm_test_review_triggered",
        "addLabel": "sm_test_review_triggered",
        "enabled": false
    },
    {
        "description": "In Rework Test Cases \u2192 trigger pr_test_automation_rework",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('In Rework')",
        "configFile": "agents/pr_test_automation_rework.json",
        "skipIfLabel": "sm_test_rework_triggered",
        "addLabel": "sm_test_rework_triggered",
        "enabled": false
    },
    {
        "description": "In Review Stories & Bugs (pr_approved) \u2192 retry merge",
        "jql": "project = {jiraProject} AND issuetype in ('Story', 'Bug') AND status in ('In Review') AND labels = 'pr_approved' ORDER BY created ASC",
        "configFile": "agents/retry_merge.json",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "In Review Test Cases (pr_approved) \u2192 retry merge",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('In Review - Passed', 'In Review - Failed') AND labels = 'pr_approved' ORDER BY created ASC",
        "configFile": "agents/retry_merge_test.json",
        "localExecution": true,
        "enabled": false
    },
    {
        "description": "Review/Rework/Blocked Stories & Bugs with already merged PR \u2192 recover Merged status",
        "jql": "project = {jiraProject} AND issuetype in ('Story', 'Bug') AND status in ('In Review', 'In Rework', 'Blocked') ORDER BY updated ASC",
        "configFile": "agents/recover_merged_pr.json",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "Blocked Stories & Bugs with all resolved dependencies \u2192 move to Backlog",
        "jql": "project = {jiraProject} AND issuetype in ('Story', 'Bug') AND status in ('Blocked') ORDER BY updated ASC",
        "configFile": "agents/unblock_resolved_dependencies.json",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "In Review Test Cases with dirty PR \u2192 move to In Rework",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('In Review - Passed', 'In Review - Failed')",
        "configFile": "agents/recover_dirty_review_test_case.json",
        "localExecution": true,
        "enabled": false
    },
    {
        "description": "Merged Stories \u2192 Ready For Testing + generate test cases",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('Merged')",
        "targetStatus": "Ready For Testing",
        "configFile": "agents/test_cases_generator.json",
        "skipIfLabel": "sm_test_cases_triggered",
        "addLabel": "sm_test_cases_triggered",
        "enabled": true
    },
    {
        "description": "Merged Bugs \u2192 Ready For Testing",
        "jql": "project = {jiraProject} AND issuetype in ('Bug') AND status in ('Merged')",
        "targetStatus": "Ready For Testing",
        "configFile": "agents/bug_merged.json",
        "skipIfLabel": "sm_bug_merged_triggered",
        "enabled": true,
        "localExecution": true
    },
    {
        "description": "Ready For Testing Bugs \u2192 generate test cases",
        "jql": "project = {jiraProject} AND issuetype in ('Bug') AND status in ('Ready For Testing') AND (labels is EMPTY OR labels NOT IN ('sm_bug_test_cases_triggered'))",
        "configFile": "agents/bug_test_cases_generator.json",
        "skipIfLabel": "sm_bug_test_cases_triggered",
        "addLabel": "sm_bug_test_cases_triggered",
        "enabled": true
    },
    {
        "description": "Ready For Testing Bugs \u2192 automate linked test cases in bulk",
        "jql": "project = {jiraProject} AND issuetype in ('Bug') AND status in ('Ready For Testing')",
        "configFile": "agents/bug_test_automation.json",
        "skipIfLabel": "sm_bug_test_automation_triggered",
        "addLabel": "sm_bug_test_automation_triggered",
        "enabled": true
    },
    {
        "description": "Ready For Testing Stories \u2192 automate linked test cases in bulk",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('Ready For Testing')",
        "configFile": "agents/story_test_automation.json",
        "skipIfLabel": "sm_story_test_automation_triggered",
        "skipIfLabels": [
            "sm_test_cases_triggered"
        ],
        "addLabel": "sm_story_test_automation_triggered",
        "enabled": true
    },
    {
        "description": "In Testing Stories \u2192 check all TCs passed \u2192 Done",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('In Testing')",
        "configFile": "agents/story_done_check.json",
        "skipIfLabel": "sm_story_done_check_triggered",
        "enabled": true,
        "localExecution": true
    },
    {
        "description": "In Testing Bugs \u2192 check all TCs passed \u2192 Done",
        "jql": "project = {jiraProject} AND issuetype in ('Bug') AND status in ('In Testing')",
        "configFile": "agents/bug_done_check.json",
        "skipIfLabel": "sm_bug_done_check_triggered",
        "enabled": true,
        "localExecution": true
    },
    {
        "description": "Failed Test Cases with linked Bugs \u2192 recover Bug To Fix",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('Failed') ORDER BY updated ASC",
        "configFile": "agents/recover_failed_tc_bug_status.json",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "Failed Test Cases \u2192 create or link bugs in batch",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('Failed') AND (labels is EMPTY OR labels NOT IN ('sm_bug_creation_triggered')) ORDER BY created ASC",
        "configFile": "agents/bulk_bugs_creation.json",
        "concurrencyKey": "bulk_bugs_creation",
        "skipIfLabel": "sm_bulk_bugs_creation_triggered",
        "addLabel": "sm_bulk_bugs_creation_triggered",
        "recoverStaleTriggerLabel": true,
        "limit": 1,
        "enabled": true
    },
    {
        "description": "Backlog / To Do / Ready For Development / In Development Bugs \u2192 trigger bug_development",
        "jql": "project = {jiraProject} AND issuetype in ('Bug') AND status in ('Backlog', 'To Do', 'Ready For Development', 'In Development', 'In Progress') AND updated <= -15m ORDER BY updated ASC",
        "configFile": "agents/bug_development.json",
        "concurrencyKey": "bug_development",
        "skipIfLabel": "sm_bug_development_triggered",
        "addLabel": "sm_bug_development_triggered",
        "limit": 1,
        "enabled": true
    },
    {
        "description": "Bug To Fix Tickets \u2192 all linked Bugs Done \u2192 move to Backlog / Ready For Testing",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case', 'Story') AND status in ('Bug To Fix')",
        "configFile": "agents/bug_to_fix_check.json",
        "skipIfLabel": "sm_bug_to_fix_check_triggered",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "Intake/In Development Tasks \u2192 all linked Stories/Bugs Done \u2192 Ready For Testing",
        "jql": "project = {jiraProject} AND issuetype in ('Task') AND status in ('In Development', 'In Progress') AND (parent = {parentTicket} OR labels in ('ai_intake'))",
        "configFile": "agents/task_done_check.json",
        "skipIfLabel": "sm_task_done_check_triggered",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "Stuck In Development Test Cases \u2192 recover (check PR, route to Rework/Review/Backlog)",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('In Development') AND updated <= -15m",
        "configFile": "agents/recover_stuck_test_case.json",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "Failed Test Cases \u2192 create or link bug (single, disabled by default \u2014 use bulk_bugs_creation instead)",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('Failed')",
        "configFile": "agents/bug_creation.json",
        "skipIfLabel": "sm_bug_creation_triggered",
        "addLabel": "sm_bug_creation_triggered",
        "limit": 5,
        "enabled": true
    },
    {
        "description": "Backlog / To Do / Ready For Development Test Cases \u2192 In Development + automate",
        "jql": "project = {jiraProject} AND issuetype in ('Test Case') AND status in ('Backlog', 'To Do', 'Ready For Development')",
        "targetStatus": "In Development",
        "configFile": "agents/test_case_automation.json",
        "skipIfLabel": "sm_test_automation_triggered",
        "addLabel": "sm_test_automation_triggered",
        "enabled": true
    },
    {
        "description": "PO Review Stories with all subtasks Done \u2192 BA Analysis",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('PO Review')",
        "configFile": "agents/story_ba_check.json",
        "skipIfLabel": "sm_story_ba_check_triggered",
        "localExecution": true,
        "enabled": true
    },
    {
        "description": "BA Analysis Stories \u2192 generate Acceptance Criteria",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('BA Analysis')",
        "configFile": "agents/story_acceptance_criteria.json",
        "skipIfLabels": [
            "sm_story_acceptance_criteria_triggered",
            "sm_story_acceptance_criterias_triggered"
        ],
        "addLabel": "sm_story_acceptance_criteria_triggered",
        "enabled": true
    },
    {
        "description": "Solution Architecture Stories \u2192 generate Solution Design",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('Solution Architecture')",
        "configFile": "agents/story_solution.json",
        "skipIfLabel": "sm_story_solution_triggered",
        "addLabel": "sm_story_solution_triggered",
        "enabled": true
    },
    {
        "description": "Subtasks with 'q' label \u2192 trigger PO refinement",
        "jql": "project = {jiraProject} AND issuetype in ('Subtask') AND labels in ('q') and status not in (Done)",
        "configFile": "agents/po_refinement.json",
        "skipIfLabel": "sm_po_refinement_triggered",
        "addLabel": "sm_po_refinement_triggered",
        "enabled": true
    },
    {
        "description": "Backlog / To Do Stories \u2192 ask clarification questions",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('Backlog', 'To Do')",
        "configFile": "agents/story_questions.json",
        "skipIfLabels": [
            "sm_story_questions_triggered",
            "ai_questions_asked"
        ],
        "addLabel": "sm_story_questions_triggered",
        "limit": 1
    },
    {
        "description": "Backlog / To Do Tasks (children of parent ticket) \u2192 run intake agent",
        "jql": "project = {jiraProject} AND issuetype in ('Task') AND status in ('Backlog', 'To Do') AND parent = {parentTicket}",
        "targetStatus": "In Development",
        "configFile": "agents/intake.json",
        "skipIfLabel": "sm_task_intake_triggered",
        "addLabel": "sm_task_intake_triggered",
        "enabled": true
    },
    {
        "description": "Ready For Development Stories \u2192 trigger story_development",
        "jql": "project = {jiraProject} AND issuetype in ('Story') AND status in ('Ready For Development')",
        "configFile": "agents/story_development.json",
        "skipIfLabel": "sm_story_development_triggered",
        "addLabel": "sm_story_development_triggered",
        "enabled": true
    }
],

    repository: {
        owner: 'IstiN',
        repo: 'trackstate'
    },

    jira: {
        project: 'TS',
        parentTicket: 'TS-1',
        questions: {
            fetchJql: 'parent = {ticketKey} AND issuetype = Subtask ORDER BY created ASC',
            answerField: 'Answer'
        },
        fields: {
            acceptanceCriteria: 'Acceptance Criteria',
            solution: 'Solution',
            diagrams: 'Diagrams',
            answer: 'Answer',
            bugSolution: 'customfield_10400',
            failedReason: 'customfield_10535'
        },
        parentContextFetch: {
            enabled: true,
            resolveFieldNames: true,
            // parentFields defaults are auto-aggregated from jira.fields above
            // + DEFAULT_FIELDS ['key','summary','description','status','comment']
            // Explicit override example:
            // parentFields: ['key','summary','description','status','Acceptance Criteria','Solution','Diagrams'],
            siblingFields: ['key', 'summary', 'description', 'status', 'comment', 'Acceptance Criteria']
        }
    },

    git: {
        baseBranch: 'main'
    },

    agentConfigsDir: 'agents',

    cliPrompts: {
        story_development: [
            GOAL_INSTRUCTIONS,
            DESIGN_REFERENCE,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/development_focus.md'
        ],
        bug_development: [
            GOAL_INSTRUCTIONS,
            DESIGN_REFERENCE,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/development_focus.md',
            BUG_DEV_ANTIPATTERNS
        ],
        bug_rca: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md'
        ],
        pr_review: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/review_focus.md'
        ],
        pr_rework: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/rework_focus.md',
            BUG_DEV_ANTIPATTERNS
        ],
        pr_test_automation_review: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/test_review_focus.md',
            TEST_AUTOMATION_ANTIPATTERNS
        ],
        pr_test_automation_rework: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/test_rework_focus.md',
            TEST_AUTOMATION_ANTIPATTERNS
        ],
        test_case_automation: [
            GOAL_INSTRUCTIONS,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            TEST_AUTOMATION_ANTIPATTERNS
        ],
        story_test_automation: [
            GOAL_INSTRUCTIONS,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            TEST_AUTOMATION_ANTIPATTERNS
        ],
        bug_test_automation: [
            GOAL_INSTRUCTIONS,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            TEST_AUTOMATION_ANTIPATTERNS
        ],
        pr_story_test_automation_review: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/test_review_focus.md',
            TEST_AUTOMATION_ANTIPATTERNS
        ],
        pr_bug_test_automation_review: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/test_review_focus.md',
            TEST_AUTOMATION_ANTIPATTERNS
        ]
    },

    // Tracker-specific CLI prompts that EXTEND the agent JSON's cliPromptsByTracker.
    // The agent submodule defines the base tracker prompts; this block only adds
    // project-specific extras. Empty objects mean "use agent defaults".
    cliPromptsByTracker: {
        jira: {},
        ado: {}
    },

    additionalInstructions: {
        po_refinement: [
            GOAL_INSTRUCTIONS,
            DESIGN_REFERENCE,
            SETUP_REPO_INSTRUCTIONS,
            './agents/instructions/common/investigate_before_answer.md',
            './.dmtools/instructions/product/trackstate_domain_knowledge.md'
        ],
        story_description: [
            GOAL_INSTRUCTIONS,
            DESIGN_REFERENCE,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/product/trackstate_domain_knowledge.md'
        ],
        story_acceptance_criteria: [
            GOAL_INSTRUCTIONS,
            DESIGN_REFERENCE,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/product/trackstate_domain_knowledge.md',
            './agents/instructions/common/investigate_before_answer.md'
        ],
        story_acceptance_criterias: [
            GOAL_INSTRUCTIONS,
            DESIGN_REFERENCE,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/product/trackstate_domain_knowledge.md',
            './agents/instructions/common/investigate_before_answer.md'
        ],
        story_questions: [
            GOAL_INSTRUCTIONS,
            DESIGN_REFERENCE,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/product/trackstate_domain_knowledge.md',
            './agents/instructions/common/investigate_before_answer.md'
        ],
        story_solution: [
            GOAL_INSTRUCTIONS,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/product/trackstate_domain_knowledge.md'
        ],
        solution_description: [
            GOAL_INSTRUCTIONS,
            SETUP_REPO_INSTRUCTIONS,
            './.dmtools/instructions/product/trackstate_domain_knowledge.md'
        ],
        story_development: [
            TRACKSTATE_FLUTTER_RULES,
            TRACKSTATE_WEB_FOCUS_RULES
        ],
        bug_development: [
            TRACKSTATE_FLUTTER_RULES,
            TRACKSTATE_WEB_FOCUS_RULES
        ],
        test_case_automation: [
            TRACKSTATE_TEST_AUTOMATION_RULES
        ],
        pr_review: [
            TRACKSTATE_FLUTTER_RULES,
            TRACKSTATE_WEB_FOCUS_RULES
        ],
        pr_rework: [
            TRACKSTATE_FLUTTER_RULES,
            TRACKSTATE_WEB_FOCUS_RULES
        ],
        pr_test_automation_review: [
            TRACKSTATE_TEST_AUTOMATION_RULES,
            TRACKSTATE_TEST_REVIEW_CHECKLIST
        ],
        pr_test_automation_rework: [
            TRACKSTATE_TEST_AUTOMATION_RULES
        ],
        story_test_automation: [
            TRACKSTATE_TEST_AUTOMATION_RULES
        ],
        story_test_automation_rework: [
            TRACKSTATE_TEST_AUTOMATION_RULES
        ],
        pr_story_test_automation_review: [
            TRACKSTATE_TEST_AUTOMATION_RULES,
            TRACKSTATE_TEST_REVIEW_CHECKLIST
        ],
        bug_test_automation: [
            TRACKSTATE_TEST_AUTOMATION_RULES,
            TRACKSTATE_BUG_TEST_AUTOMATION_SCOPE
        ],
        bug_test_automation_rework: [
            TRACKSTATE_TEST_AUTOMATION_RULES,
            TRACKSTATE_BUG_TEST_AUTOMATION_SCOPE
        ],
        pr_bug_test_automation_review: [
            TRACKSTATE_TEST_AUTOMATION_RULES,
            TRACKSTATE_TEST_REVIEW_CHECKLIST
        ],
        bug_creation: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/product/trackstate_domain_knowledge.md'
        ],
        df_manager: [
            './.dmtools/instructions/agents/df_manager_watchlist.md'
        ]
    },

    jobParamPatches: {
        test_cases_generator: {
            confluencePages: [
                GOAL_INSTRUCTIONS,
                DESIGN_REFERENCE,
                './agents/instructions/test_cases/test_case_creation_rules.md',
                './.dmtools/instructions/test_cases/trackstate_functional_test_case_rules.md'
            ],
            postJSAction: 'agents/js/triggerStoryTestAutomation.js',
            customParams: {
                autoStartStoryTestAutomation: true,
                autoStartStoryTestAutomationConfigFile: 'agents/story_test_automation.json'
            }
        },
        bug_test_cases_generator: {
            postJSAction: 'agents/js/triggerBugTestAutomation.js',
            customParams: {
                autoStartBugTestAutomation: true,
                autoStartBugTestAutomationConfigFile: 'agents/bug_test_automation.json'
            }
        },
        story_questions: {
            customParams: {
                autoStartQuestionAnswer: true,
                autoStartQuestionAnswerConfigFile: 'agents/po_refinement.json'
            }
        },
        story_acceptance_criteria: {
            customParams: {
                autoStartSolution: true,
                autoStartSolutionConfigFile: 'agents/story_solution.json'
            }
        },
        story_acceptance_criterias: {
            customParams: {
                autoStartSolution: true,
                autoStartSolutionConfigFile: 'agents/story_solution.json'
            }
        },
        story_solution: {
            customParams: {
                autoStartDevelopment: true,
                autoStartDevelopmentConfigFile: 'agents/story_development.json'
            }
        },
        story_development: {
            customParams: {
                autoStartReview: true,
                autoStartReviewConfigFile: 'agents/pr_review.json',
                managedSubmodules: TRACKSTATE_SETUP_SUBMODULES,
                feedbackLoop: FLUTTER_FEEDBACK
            }
        },
        bug_development: {
            customParams: {
                autoStartReview: true,
                autoStartReviewConfigFile: 'agents/pr_review.json',
                managedSubmodules: TRACKSTATE_SETUP_SUBMODULES,
                feedbackLoop: FLUTTER_FEEDBACK
            }
        },
        test_case_automation: {
            customParams: {
                autoStartReview: true,
                autoStartReviewConfigFile: 'agents/pr_test_automation_review.json'
            }
        },
        pr_review: {
            customParams: {
                autoStartRework: true,
                autoStartReworkConfigFile: 'agents/pr_rework.json',
                // If the PR already has this many review threads/comments, allow
                // an APPROVE verdict to stand even when suggestions remain, so the
                // review/rework loop eventually terminates.
                maxReviewThreadsBeforeForceApprove: 100
            }
        },
        pr_test_automation_review: {
            customParams: {
                autoStartRework: true,
                autoStartReworkConfigFile: 'agents/pr_test_automation_rework.json',
                maxReviewThreadsBeforeForceApprove: 100
            }
        },
        pr_rework: {
            customParams: {
                autoStartReview: true,
                autoStartReviewConfigFile: 'agents/pr_review.json',
                managedSubmodules: TRACKSTATE_SETUP_SUBMODULES,
                feedbackLoop: FLUTTER_FEEDBACK
            }
        },
        pr_test_automation_rework: {
            customParams: {
                autoStartReview: true,
                autoStartReviewConfigFile: 'agents/pr_test_automation_review.json',
                feedbackLoop: POST_ACTION_FEEDBACK
            }
        },
        story_test_automation: {
            customParams: {
                autoStartReview: false
            }
        },
        story_test_automation_rework: {
            customParams: {
                autoStartReview: false,
                removeLabel: 'sm_story_test_rework_triggered',
                feedbackLoop: POST_ACTION_FEEDBACK
            }
        },
        pr_story_test_automation_review: {
            customParams: {
                autoStartMerge: false,
                autoStartRework: false,
                maxReviewThreadsBeforeForceApprove: 100,
                smFallback: true
            }
        },
        bug_test_automation: {
            customParams: {
                autoStartReview: false
            }
        },
        bug_test_automation_rework: {
            customParams: {
                autoStartReview: false,
                removeLabel: 'sm_bug_test_rework_triggered',
                feedbackLoop: POST_ACTION_FEEDBACK
            }
        },
        pr_bug_test_automation_review: {
            customParams: {
                autoStartMerge: false,
                autoStartRework: false,
                maxReviewThreadsBeforeForceApprove: 100,
                smFallback: true
            }
        },
        retry_merge: {
            customParams: {
                autoStartRework: true,
                autoStartReworkConfigFile: 'agents/pr_rework.json'
            }
        },
        retry_merge_test: {
            customParams: {
                autoStartRework: true,
                autoStartReworkConfigFile: 'agents/pr_test_automation_rework.json'
            }
        }
    },

    agentParamPatches: {},

    smRuleOverrides: {
        'agents/test_case_automation.json': {
            enabled: false
        }
    }
};
