from datetime import datetime, timezone


def list_ecr(ecr, max_age_days):
    now = datetime.now(timezone.utc)
    old_images = []
    response = ecr.describe_repositories()
    for repo in response["repositories"]:
        images = ecr.describe_images(repositoryName=repo["repositoryName"])
        for image in images["imageDetails"]:
            age = (now - image["imagePushedAt"]).days
            image["AgeDays"] = age

            if age > max_age_days:
                old_images.append(image)

    return old_images
