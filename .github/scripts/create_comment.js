const github = require('@actions/github');
const core = require('@actions/core');

async function run() {
    try {
        const tags = process.env.TAG_MAP || '[]';

        let comment = '## Modified Steps Check\n\n';

        // Add tags section with formatting
        comment += '\n### Steps and Tags with Version Bump Options:\n$START\n';

        // Parse the TAG_MAP JSON
        const parsedTags = JSON.parse(tags);

        if (parsedTags && parsedTags.length > 0) {
            parsedTags.forEach(([step, currentTag]) => {
                // Format the output: step | [latest_tag] -> ["patch"]
                comment += `${step} | [${currentTag}]\t['patch']\n`;
            });
        } else {
            comment += '_No matching tags found_\n';
        }

        comment += '\n⚠️ Please review these changes carefully before merging.';

        // Create a comment on the PR or issue
        await github.rest.issues.createComment({
            owner: github.context.repo.owner,
            repo: github.context.repo.repo,
            issue_number: github.context.issue.number,
            body: comment
        });
    } catch (error) {
        core.setFailed(`Action failed with error: ${error}`);
        console.log('Error details:', error);
    }
}

run();
