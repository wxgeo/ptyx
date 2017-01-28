from __future__ import division, unicode_literals, absolute_import, print_function

import os, sys, locale
import subprocess
import tempfile
import shutil

from latexgenerator import compiler
from config import param


class CustomOutput(object):
    def __init__(self, logfile_name = ''):
        self.log_file_created = False
        self.logfile_name = logfile_name

    def write(self, string_):
        try:
            sys.__stdout__.write(string_)
            if self.logfile_name:
                with open(self.logfile_name, 'a', encoding='utf-8') as f:
                    f.write(string_)

        except Exception:
            sys.stderr = sys.__stderr__
            raise

    def flush(self):
        sys.__stdout__.flush()


def execute(string, quiet=False):
    out = subprocess.Popen(string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    encoding = locale.getpreferredencoding(False)
    output = out.read().decode(encoding, errors='replace')
    sys.stdout.write(output)
    out.close()
    if not quiet:
        print("Command '%s' executed." %string)
    return output



def make_files(input_name, correction=False, **options):
    formats = options.get('formats', param['formats'])
    names = options.get('names', [])

    # Choose output names
    os.chdir(os.path.split(input_name)[0])
    if input_name.endswith('.ptyx'):
        output_name = input_name[:-5]
    elif input_name.endswith('.tex'):
        output_name = input_name[:-4]
        if 'tex' in formats:
            output_name += '_'
        # the trailing _ avoids name conflicts with the .tex file generated
    else:
        output_name = input_name + '_'

    head, tail = os.path.split(output_name)

    if correction:
        output_name += '-corr'
        # Following prevent auto_make_dir option to result in a subdirectory
        # for correction (this is bad for pictures).
        head += '-corr'
        tail += '-corr'

    if options.get('auto_make_dir'):
        # Test if the .ptyx file is already in a directory with same name.
        options['make_directory'] = (os.path.split(head)[1] != tail)
    if options.get('make_directory'):
        # Create a directory with the same name than the .ptyx file,
        # which will contain all generated files.
        if not os.path.isdir(tail):
            os.mkdir(tail)
        output_name = output_name + os.sep + tail

        print(output_name)

    filenames = []
    start = options.get('start', 1)
    n = options.get('number', param['total'])
    for num in range(start, start + n):
        if names:
            name = names[num - 1]
            filename = '%s-%s' % (output_name, name)
        else:
            name = ''
            filename = ('%s-%s' % (output_name, num) if n > 1
                        else output_name)
        #~ filename = filename.replace(' ', '\ ')
        filenames.append(filename)

        # Output is redirected to a .log file
        sys.stdout = sys.stderr = CustomOutput((filename + '-python.log')
                                              if not options.get('remove') else '')
        options.setdefault('context', {})
        options['context'].update(WITH_ANSWERS=correction, NUM=num, NAME=name,
                                  TOTAL=n)
        make_file(filename, **options)

    return filenames, output_name



def _compile_latex_file(filename, dest=None, quiet=False):
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
    log = execute(command)
    # Run command twice if references were found.
    if 'Rerun to get cross-references right.' in log or \
       'There were undefined references.' in log:
        log = execute(command)


def make_file(output_name, **options):
    remove = options.get('remove')
    quiet = options.get('quiet')
    formats = options.get('formats', param['formats'])

    # make_file() can be used to compile plain LaTeX too.
    latex = options.get('plain_latex')
    if latex is None:
        context = options.get('context', {})
        context.setdefault('NUM', 1)
        context.setdefault('TOTAL', 1)

        latex = compiler.generate_latex(**context)

    if 'tex' in formats:
        with open(output_name + '.tex', 'w') as texfile:
            texfile.write(latex)
            if 'pdf' in formats:
                texfile.flush()
                _compile_latex_file(texfile.name, quiet=quiet)
                if remove:
                    for extension in ('aux', 'log', 'out'):
                        name = '%s.%s' % (output_name, extension)
                        if os.path.isfile(name):
                            os.remove(name)
    else:
        # FIXME:
        # - Don't work with pgfplot !!!
        # - Difficult to debug.
        # - Seems to be problem with references too.
        assert 'pdf' in formats

        with tempfile.TemporaryDirectory() as tmp_path:
            tmp_name = os.path.join(tmp_path, os.path.basename(output_name))
            with open(tmp_name + '.tex', 'w') as texfile:
                texfile.write(latex)
                texfile.flush()
                _compile_latex_file(texfile.name, quiet=quiet)
            shutil.move(tmp_name + '.pdf', output_name + '.pdf')


def join_files(output_name, filenames, seed_file_name=None, **options):
    "Join different versions in a single pdf, then compress it if asked to."
    number = len(filenames)
    if options.get('compress') or (options.get('cat') and number > 1):
        # pdftk and ghostscript must be installed.
        filenames = [filename + '.pdf' for filename in filenames]
        pdf_name = output_name + '.pdf'
        if number > 1:
            files = ' '.join('"%s"' % filename for filename in filenames)
            print('Pdftk output:')
            print(execute('pdftk %s output "%s"' % (files, pdf_name)))
            if options.get('remove_all'):
                for name in filenames:
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
