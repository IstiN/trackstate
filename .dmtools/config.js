/**
 * TrackState project configuration for DMTools agents.
 *
 * The shared agents submodule resolves this file from ../.dmtools/config.js.
 * Jira project values are wired to the TrackState Jira project.
 */
const GOAL_INSTRUCTIONS = './.dmtools/instructions/goal/goal.md';
const DESIGN_REFERENCE = './.dmtools/instructions/goal/DESIGN.md';
const SETUP_REPO_INSTRUCTIONS = './.dmtools/instructions/product/trackstate_setup_repo.md';
const TRACKSTATE_SETUP_SUBMODULES = [{ path: 'trackstate-setup', branch: 'main' }];

module.exports = {
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
                managedSubmodules: TRACKSTATE_SETUP_SUBMODULES
            }
        },
        bug_development: {
            customParams: {
                autoStartReview: true,
                autoStartReviewConfigFile: 'agents/pr_review.json',
                managedSubmodules: TRACKSTATE_SETUP_SUBMODULES
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
                managedSubmodules: TRACKSTATE_SETUP_SUBMODULES
            }
        },
        pr_test_automation_rework: {
            customParams: {
                autoStartReview: true,
                autoStartReviewConfigFile: 'agents/pr_test_automation_review.json'
            }
        }
    },

    agentParamPatches: {}
};
