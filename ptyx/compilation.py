import os, sys, locale, re
import subprocess
import tempfile
import shutil
from os.path import dirname, basename, join, isdir, isfile
from os import chdir, mkdir

from ptyx.latexgenerator import compiler
from ptyx.config import param


class _LoggedStream(object):
    """Add logging to a data stream, like stdout or stderr.

    * `logfile` is a file already opened in apending mode ;
    * `default` is default output (`sys.stdout` or `sys.stderr`).
    """
    def __init__(self, logfile, default):
        self.logfile = logfile
        self.default = default

    def write(self, s):
        self.default.write(s)
        self.logfile.write(s)

    def flush(self):
        self.default.flush()
        self.logfile.flush()


class _DevNull(object):
    def write(self, *_): pass
    close = flush = write


class Logging(object):
    """Context manager. All output (sys.stdout/stderr) will be logged in a file.

    Note this logging occurs in addition to standard output, which is not suppressed.
    """
    def __init__(self, logfile_name=''):
        self.logfile = (open(logfile_name, 'a') if logfile_name else _DevNull())

    def __enter__(self):
        self.previous = {'stdout': sys.stdout, 'stderr': sys.stderr}
        sys.stdout = _LoggedStream(self.logfile, sys.stdout)
        sys.stderr = _LoggedStream(self.logfile, sys.stderr)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        sys.stdout = sys.stdout.default
        sys.stderr = sys.stderr.default
        self.logfile.close()


def execute(string, quiet=False):
    out = subprocess.Popen(string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    encoding = locale.getpreferredencoding(False)
    output = out.read().decode(encoding, errors='replace')
    sys.stdout.write(output)
    out.close()
    if not quiet:
        print("Command '%s' executed." %string)
    return output



def make_files(input_name, correction=False, _nums=None, **options):
    # `_nums` is used when generating the answers of the quiz.
    # In the first pass, when generating the quizzes, some numbers may
    # have been skipped (because they don't satisfy the page number constraint).
    if _nums is not None:
        assert correction
        _nums = list(_nums) # make a copy

    formats = options.get('formats', param['formats'])
    names = options.get('names', [])

    chdir(dirname(input_name))

    # Create an empty `.compile/{input_name}` subfolder.
    if not isdir('.compile'):
        mkdir('.compile')
        # XXX: handle errors (e.g `.compile` might be an existing file).
    compilation_dir = join(dirname(input_name), '.compile', basename(input_name))

    if not correction and isdir(compilation_dir):
        shutil.rmtree(compilation_dir)
    if not isdir(compilation_dir):
        mkdir(compilation_dir)

    # Choose output names
    if input_name.endswith('.ptyx'):
        output_name = input_name[:-5]
    elif input_name.endswith('.tex'):
        output_name = input_name[:-4]
        if 'tex' in formats:
            output_name += '_'
        # the trailing _ avoids name conflicts with the .tex file generated
    else:
        output_name = input_name + '_'
    output_name = join(compilation_dir, basename(output_name))

    if correction:
        output_name += '-corr'

    filenames = []
    nums = []
    n = options.get('number', param['total'])
    total = 0
    num = options.get('start', 1)
    while total < n:
        if _nums:
            num = _nums.pop(0)
        if names:
            name = names[total]
            filename = '%s-%s' % (output_name, name)
        else:
            name = ''
            filename = ('%s-%s' % (output_name, num) if n > 1
                        else output_name)

        options.setdefault('context', {})
        options['context'].update(WITH_ANSWERS=correction, NUM=num, NAME=name,
                                  TOTAL=n)

        # Output is redirected to a .log file
        logfile = (filename + '-python.log')
        print('\nLog file:', logfile, '\n')
        with Logging(logfile if not options.get('remove') else ''):
            infos = make_file(filename, **options)

        pages = infos.get('pages_number')
        target = options.get('filter_by_pages_number')
        if not correction and pages and target and pages != target:
             print('Warning: skipping %s (incorrect page number) !' % filename)
        else:
            total += 1
            filenames.append(filename)
            nums.append(num)
        num += 1

    assert len(filenames) == n
    # ~ if len(filenames) < n:
        # ~ msg1 = ('Warning: only %s pdf files generated (not %s) !' % (len(filenames), n))
        # ~ msg2 = '(Unreleased pdf did not match page number constraints).'
        # ~ sep = max(len(msg1), len(msg2))*'~'
        # ~ print('\n'.join(('', sep, msg1, msg2, sep, '')))

    # Join different versions in a single pdf, and compress if asked to.
    join_files(output_name, filenames, **options)


    if options.get('generate_batch_for_windows_printing'):
        name = "print%s.bat" % ('_corr' if correction else '')
        bat_file_name = os.path.join(os.path.dirname(input_name), name)
        with open(bat_file_name, 'w') as bat_file:
            bat_file.write(param['win_print_command'] + ' '.join('%s.pdf'
                                  % os.path.basename(f) for f in filenames))

    # Copy pdf file to parent directory.
    for ext in formats:
        name = f'{output_name}.{ext}'
        if isfile(name):
            shutil.copy(name, dirname(input_name))
        else:
            for filename in filenames:
                name = f'{filename}.{ext}'
                shutil.copy(name, dirname(input_name))
    # Remove `.compile` folder if asked to.
    if options.get('remove'):
        shutil.rmtree(compilation_dir)

    return filenames, output_name, nums



def make_file(output_name, **options):
    infos = {}
    quiet = options.get('quiet')
    formats = options.get('formats', param['formats'])

    # make_file() can be used to compile plain LaTeX too.
    latex = options.get('plain_latex')
    if latex is None:
        context = options.get('context', {})
        context.setdefault('NUM', 1)
        context.setdefault('TOTAL', 1)

        latex = compiler.generate_latex(**context)

    with open(output_name + '.tex', 'w') as texfile:
        texfile.write(latex)
        if 'pdf' in formats:
            texfile.flush()
            pages_number = _compile_latex_file(texfile.name, quiet=quiet)
            infos['pages_number'] = pages_number
    return infos



def _compile_latex_file(filename, dest=None, quiet=False):
    """Compile the latex file and return the number of pages of the pdf
    (or None if not found)."""
    # By default, pdflatex use current directory as destination folder.
    # However, much of the time, we want destination folder to be the one
    # where the tex file was found.
    if dest is None:
        dest = os.path.dirname(filename)
    if quiet:
        command = param['quiet_tex_command']
    else:
        command = param['tex_command']
    command += ' -output-directory "%s" "%s"' % (dest, filename)
    # ~ input('- run -')
    log = execute(command)
    # Run command twice if references were found.
    if 'Rerun to get cross-references right.' in log or \
       'There were undefined references.' in log:
        # ~ input('- run again -')
        log = execute(command)

    # Return the number of pages of the pdf generated.
    pattern = r'Output written on .+ \(([0-9]+) pages, [0-9]+ bytes\)\.'
    m = re.search(pattern, log, flags=re.DOTALL)
    return (int(m.group(1)) if m is not None else None)



def join_files(output_name, pdfnames, seed_file_name=None, **options):
    "Join different versions in a single pdf, then compress it if asked to."
    number = len(pdfnames)
    if options.get('compress') or options.get('cat'):
        # Nota: don't exclude the case `number == 1`,
        # since the following actions rename file,
        # so excluding the case `number == 1` would break autoqcm scan for example.
        # pdftk and ghostscript must be installed.
        pdfnames = [filename + '.pdf' for filename in pdfnames]
        pdf_name = output_name + '.pdf'
        files = ' '.join('"%s"' % filename for filename in pdfnames)
        print('Pdftk output:')
        print(execute('pdftk %s output "%s"' % (files, pdf_name)))
        if options.get('remove_all'):
            for name in pdfnames:
                os.remove(name)
        if options.get('compress'):
            temp_dir = tempfile.mkdtemp()
            compressed_pdf_name = os.path.join(temp_dir, 'compresse.pdf')
            command = \
                """command pdftops \
                -paper match \
                -nocrop \
                -noshrink \
                -nocenter \
                -level3 \
                -q \
                "%s" - \
                | command ps2pdf14 \
                -dEmbedAllFonts=true \
                -dUseFlateCompression=true \
                -dProcessColorModel=/DeviceCMYK \
                -dConvertCMYKImagesToRGB=false \
                -dOptimize=true \
                -dPDFSETTINGS=/prepress \
                - "%s" """ % (pdf_name, compressed_pdf_name)
            os.system(command)
            old_size = os.path.getsize(pdf_name)
            new_size = os.path.getsize(compressed_pdf_name)
            if new_size < old_size:
                shutil.copyfile(compressed_pdf_name, pdf_name)
                print('Compression ratio: {0:.2f}'.format(old_size/new_size))
            else:
                print('Warning: compression failed.')
            if seed_file_name is not None:
                temp_dir = tempfile.mkdtemp()
                pdf_with_seed = os.path.join(temp_dir, 'with_seed.pdf')
                execute('pdftk "%s" attach_files "%s" output "%s"' % (pdf_name, seed_file_name, pdf_with_seed))
                shutil.copyfile(pdf_with_seed, pdf_name)
        if number > 1:
            print('%s files merged.' %len(pdfnames))

    if options.get('reorder_pages'):
        # Use pdftk to detect how many pages has the pdf document.
        n = int(execute('pdftk %s dump_data output | grep -i NumberOfPages:' % pdf_name).strip().split()[-1])
        mode = options.get('reorder_pages')
        if mode == 'brochure':
            if n%4:
                raise RuntimeError('Page number is %s, but must be a multiple of 4.' % n)
            order = []
            for i in range(int(n/4)):
                order.extend([2*i + 1, 2*i + 2, n - 2*i - 1, n - 2*i])
        elif mode == 'brochure-reversed':
            if n%4:
                raise RuntimeError('Page number is %s, but must be a multiple of 4.' % n)
            order = n*[0]
            for i in range(int(n/4)):
                order[2*i] = 4*i + 1
                order[2*i + 1] = 4*i + 2
                order[n - 2*i - 2] = 4*i + 3
                order[n - 2*i - 1] = 4*i + 4
        else:
            raise NameError('Unknown mode %s for option --reorder-pages !' % mode)
        # monfichier.pdf -> monfichier-brochure.pdf
        new_name = '%s-%s.pdf' % (pdf_name[:pdf_name.index('.')], mode)
        execute('pdftk %s cat %s output %s' % (pdf_name, ' '.join(str(i) for i in order), new_name))

