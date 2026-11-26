# EC2 deployment

The GitHub Actions workflow runs tests and publishes immutable `sha-<commit>` images on pushes to `main`. EC2 deployment is a separate manual workflow dispatch so a push cannot unexpectedly replace the live application.

## One-time setup

1. Make both GHCR packages public; this workflow expects EC2 to pull them without a registry credential:
   - `ghcr.io/abhiw2/fort-3d-reconstruction-ml-api`
   - `ghcr.io/abhiw2/fort-3d-reconstruction-ml-web`
   Public packages are downloadable by anyone. Private packages are not supported by this workflow yet; their pull will fail before the Compose services are changed.
2. Ensure the EC2 instance has an instance profile with `AmazonSSMManagedInstanceCore` and appears Online in Systems Manager.
3. Create an AWS IAM role for GitHub Actions using the `token.actions.githubusercontent.com` OIDC provider. Restrict its trust policy to audience `sts.amazonaws.com` and subject `repo:AbhiW2/fort-3d-reconstruction-ml:ref:refs/heads/main`.
4. Give that role only `ssm:SendCommand` for the EC2 instance and the `AWS-RunShellScript` document, plus `ssm:GetCommandInvocation` for command status/output. No SSH key or inbound SSH rule is needed.
5. Add these repository Actions variables under **Settings → Secrets and variables → Actions → Variables**:
   - `AWS_DEPLOY_ROLE_ARN`: the role ARN from step 3.
   - `AWS_REGION`: `ap-south-1`.
   - `EC2_INSTANCE_ID`: `i-03a2608633b25adce`.

## Deploy

From the repository's **Actions** tab, open **CI and GHCR publish**, choose **Run workflow** on `main`, and start it. The job checks that the current commit's images exist, uses OIDC to assume the AWS role, and invokes SSM. On EC2 it discovers the currently running Compose API/web project, layers in the commit-pinned GHCR images, preserves the existing Compose mounts and settings, then checks API and web health. If startup or health checks fail, it attempts to restore the previous container images.

The deployment expects the existing EC2 application to be a running Docker Compose project with `api` and `web` services corresponding to `Fort_project/compose.yaml`. It fails before changing containers if it cannot identify that project. If deployment fails during this discovery stage, use the SSM command output and confirm the current container labels and Compose service names before retrying.
