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
            { name: 'flutter-test', command: 'flutter test --coverage', maxAttempts: 2 }
        ]
    },
    policyGates: {
        enabled: true,
        gates: [
            { name: 'theme-token-lint', command: 'dart run tool/check_theme_tokens.dart', maxAttempts: 2 }
        ]
    }
};

module.exports = {
    // SM parallelism: number of workflows SM dispatches per run (overrides sm.json default)
    smMaxWorkflows: 5,

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
            acceptanceCriteria: 'Acceptance Criteria'
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
            './.dmtools/prompts/development_focus.md'
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
            './.dmtools/prompts/rework_focus.md'
        ],
        pr_test_automation_review: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/test_review_focus.md'
        ],
        pr_test_automation_rework: [
            GOAL_INSTRUCTIONS,
            './.dmtools/instructions/architecture/trackstate_scope.md',
            './.dmtools/prompts/test_rework_focus.md'
        ]
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
            TRACKSTATE_FLUTTER_RULES
        ],
        bug_development: [
            TRACKSTATE_FLUTTER_RULES
        ],
        test_case_automation: [
            TRACKSTATE_TEST_AUTOMATION_RULES
        ],
        pr_review: [
            TRACKSTATE_FLUTTER_RULES
        ],
        pr_rework: [
            TRACKSTATE_FLUTTER_RULES
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
