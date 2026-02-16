import json
import os
import linkedin.commands.command as command
import linkedin.utils.linkedin as linkedin
import linkedin.utils.markdown as markdown
import logging


logger = logging.getLogger(__name__)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POSTS_DIR = os.path.join(PROJECT_ROOT, "posts")
ATTACHMENTS_DIR = os.path.join(PROJECT_ROOT, "posts", "attachments")
PUBLISHED_FILE = os.path.join(PROJECT_ROOT, "posts", ".published.json")


def _load_published():
    if os.path.isfile(PUBLISHED_FILE):
        with open(PUBLISHED_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_published(data):
    with open(PUBLISHED_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def _record_publish(filename, post_urn):
    if not post_urn:
        return
    published = _load_published()
    published[filename] = post_urn
    _save_published(published)


def _content_start_index(args):
    """Return the index where content args begin, skipping 'post' and visibility flags."""
    start = 1  # skip 'post'
    if len(args) > 1 and args[1] in ('-v', '--visibility'):
        start = 3
    elif len(args) > 1 and (args[1].startswith('--visibility=') or args[1].startswith('-v=')):
        start = 2
    return start


def _parse_post_args(args):
    """Parse post arguments, returning (content_text, image_paths).

    In file mode, post files are read from posts/ and attachments from
    posts/attachments/. Otherwise treat the last arg as inline text.
    """
    content_args = args[_content_start_index(args):]

    if not content_args:
        raise ValueError("No content provided")

    first_arg = content_args[0]
    post_file = os.path.join(POSTS_DIR, first_arg)

    if os.path.isfile(post_file):
        with open(post_file, 'r') as f:
            content_text = markdown.markdown_to_linkedin(f.read())
        image_paths = []
        for name in content_args[1:]:
            attachment = os.path.join(ATTACHMENTS_DIR, name)
            if not os.path.isfile(attachment):
                raise FileNotFoundError("Attachment not found: " + attachment)
            image_paths.append(attachment)
        return content_text, image_paths

    # If it looks like a filename but doesn't exist in posts/, error out
    if '.' in first_arg:
        raise FileNotFoundError("Post file not found: " + post_file)

    return args[-1], []


class HelpCommand(command.BaseCommand):
    def execute(self, args):
        print("usage: linkedin post [-options] \"content ...\"")
        print("       linkedin post [-options] content.md [image1.jpg image2.jpg ...]")
        print("       linkedin post list")
        print("       linkedin post delete <filename>")
        print("       linkedin attachment list")
        print("""
        Options:
            -v, --visibility=connections: When sharing, set visibility as connections or public (default public).

        File mode:
            Post text files are read from the posts/ directory.
            Image attachments are read from posts/attachments/.

            Example: linkedin post graduation.md photo1.jpg photo2.jpg
              reads posts/graduation.md and attaches
              posts/attachments/photo1.jpg, posts/attachments/photo2.jpg
        """)


class PostListCommand(command.BaseCommand):
    def execute(self, args):
        if not os.path.isdir(POSTS_DIR):
            print("No posts/ directory found.")
            return
        files = [f for f in os.listdir(POSTS_DIR)
                 if os.path.isfile(os.path.join(POSTS_DIR, f)) and not f.startswith('.')]
        if not files:
            print("No post files found in posts/")
            return
        published = _load_published()
        files.sort()
        print("Posts:")
        for f in files:
            status = " [published]" if f in published else ""
            print("  " + f + status)


class AttachmentListCommand(command.BaseCommand):
    def execute(self, args):
        if not os.path.isdir(ATTACHMENTS_DIR):
            print("No posts/attachments/ directory found.")
            return
        files = [f for f in os.listdir(ATTACHMENTS_DIR)
                 if os.path.isfile(os.path.join(ATTACHMENTS_DIR, f)) and not f.startswith('.')]
        if not files:
            print("No attachments found in posts/attachments/")
            return
        files.sort()
        print("Attachments:")
        for f in files:
            print("  " + f)


class PostDeleteCommand(command.BaseCommand):
    def execute(self, args):
        if len(args) < 3:
            print("usage: linkedin post delete <filename> [filename2 ...]")
            return
        filenames = args[2:]
        published = _load_published()
        li = linkedin.Linkedin()
        for filename in filenames:
            post_urn = published.get(filename)
            if not post_urn:
                print("No published post found for: " + filename)
                continue
            li.delete_post(post_urn)
            del published[filename]
            logger.info("Post %s is deleted!", filename)
        _save_published(published)


def _do_post(args, visibility):
    content, image_paths = _parse_post_args(args)
    li = linkedin.Linkedin()
    if image_paths:
        post_urn = li.post_with_images(visibility, content, image_paths)
    else:
        post_urn = li.post(visibility, content)
    start = _content_start_index(args)
    filename = args[start] if start < len(args) else None
    if filename and os.path.isfile(os.path.join(POSTS_DIR, filename)):
        _record_publish(filename, post_urn)


class PostConnectionsCommand(command.BaseCommand):
    def execute(self, args):
        _do_post(args, linkedin.MemberNetworkVisibility.CONNECTIONS)


class PostPublicCommand(command.BaseCommand):
    def execute(self, args):
        _do_post(args, linkedin.MemberNetworkVisibility.PUBLIC)
