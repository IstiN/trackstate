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

    globalAdditionalInstructions: [
        './agents/prompts/codegraph_tools.md'
    ],
    // SM parallelism: allow two active AI teammate runs while keeping a cap for Copilot rate-limit control.
    smMaxWorkflows: 2,

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
            bugSolution: 'customfield_10400'
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
        ]
    },

    cliPromptsByTracker: {
        jira: {
            story_questions: ['./agents/instructions/tracker/jira_markup_transform.md'],
            story_description: ['./agents/instructions/tracker/jira_markup_transform.md'],
            story_acceptance_criteria: [
                './agents/instructions/story/enhanced_story_formatting.md',
                './agents/instructions/tracker/jira_markup_transform.md'
            ],
            story_acceptance_criterias: [
                './agents/instructions/story/enhanced_story_formatting.md',
                './agents/instructions/tracker/jira_markup_transform.md'
            ],
            story_solution: [
                './agents/instructions/common/jira_context.md',
                './agents/instructions/tracker/jira_markup_transform.md',
                './agents/instructions/enhancement/solution_design_ac_reference_format.md'
            ],
            solution_description: [
                './agents/instructions/common/jira_context.md',
                './agents/instructions/tracker/jira_markup_transform.md'
            ],
            po_refinement: ['./agents/instructions/tracker/jira_markup_transform.md'],
            bug_creation: ['./agents/instructions/tracker/jira_comment_format.md'],
            bulk_bugs_creation: ['./agents/instructions/tracker/jira_comment_format.md'],
            intake: ['./agents/instructions/tracker/jira_comment_format.md'],
            pr_review: ['./agents/instructions/tracker/jira_comment_format.md'],
            pr_rework: ['./agents/instructions/tracker/jira_comment_format.md'],
            pr_test_automation_review: ['./agents/instructions/tracker/jira_comment_format.md'],
            pr_test_automation_rework: ['./agents/instructions/tracker/jira_comment_format.md'],
            test_case_automation: ['./agents/instructions/tracker/jira_comment_format.md']
        },
        ado: {
            story_questions: ['./agents/instructions/tracker/ado_markup_transform.md'],
            story_description: ['./agents/instructions/tracker/ado_markup_transform.md'],
            story_acceptance_criteria: [
                './agents/instructions/story/enhanced_story_formatting.md',
                './agents/instructions/tracker/ado_markup_transform.md'
            ],
            story_acceptance_criterias: [
                './agents/instructions/story/enhanced_story_formatting.md',
                './agents/instructions/tracker/ado_markup_transform.md'
            ],
            story_solution: [
                './agents/instructions/tracker/ado_context.md',
                './agents/instructions/tracker/ado_markup_transform.md',
                './agents/instructions/enhancement/solution_design_ac_reference_format.md'
            ],
            solution_description: [
                './agents/instructions/tracker/ado_context.md',
                './agents/instructions/tracker/ado_markup_transform.md'
            ],
            po_refinement: ['./agents/instructions/tracker/ado_markup_transform.md'],
            bug_creation: ['./agents/instructions/tracker/ado_comment_format.md'],
            bulk_bugs_creation: ['./agents/instructions/tracker/ado_comment_format.md'],
            intake: ['./agents/instructions/tracker/ado_comment_format.md'],
            pr_review: ['./agents/instructions/tracker/ado_comment_format.md'],
            pr_rework: ['./agents/instructions/tracker/ado_comment_format.md'],
            pr_test_automation_review: ['./agents/instructions/tracker/ado_comment_format.md'],
            pr_test_automation_rework: ['./agents/instructions/tracker/ado_comment_format.md'],
            test_case_automation: ['./agents/instructions/tracker/ado_comment_format.md']
        }
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
            ]
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
                autoStartReworkConfigFile: 'agents/pr_rework.json'
            }
        },
        pr_test_automation_review: {
            customParams: {
                autoStartRework: true,
                autoStartReworkConfigFile: 'agents/pr_test_automation_rework.json'
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

    agentParamPatches: {}
};
