from __future__ import division # 1/2 == .5 (par defaut, 1/2 == 0)

import os, sys
import subprocess

from latexgenerator import latex_generator
from config import param


class CustomOutput(object):
    def __init__(self, logfile_name = ''):
        self.log_file_created = False
        self.logfile_name = logfile_name

    def write(self, string_):
        try:
            if isinstance(string_, unicode):
                string_ = string_.encode('utf8')
            sys.__stdout__.write(string_)
            if self.logfile_name:
                try:
                    f = open(self.logfile_name, 'a')
                    f.write(string_)
                finally:
                    f.close()
        except Exception:
            sys.stderr = sys.__stderr__
            raise


def execute(string, quiet=False):
    out = subprocess.Popen(string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    output = out.read()
    sys.stdout.write(output)
    out.close()
    if not quiet:
        print "Command '%s' executed." %string
    return output



def make_files(input_name, syntax_tree, options, start, names, make_tex, formats, correction=False):
    # Choose output names
    os.chdir(os.path.split(input_name)[0])
    if input_name.endswith('.ptyx'):
        output_name = input_name[:-5]
    elif input_name.endswith('.tex'):
        output_name = input_name[:-4]
        if make_tex:
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

    if options.auto_make_dir:
        # Test if the .ptyx file is already in a directory with same name.
        options.make_directory = (os.path.split(head)[1] != tail)
    if options.make_directory:
        # Create a directory with the same name than the .ptyx file,
        # which will contain all generated files.
        if not os.path.isdir(tail):
            os.mkdir(tail)
        output_name = output_name + os.sep + tail

        print output_name



    filenames = []
    for num in xrange(start, start + options.number):
        latex_generator.clear()
        latex_generator.context['WITH_ANSWERS'] = correction
        latex_generator.context['NUM'] = num
        if names:
            name = names[num]
            filename = '%s-%s' % (output_name, name)
        else:
            name = ''
            filename = ('%s-%s' % (output_name, num) if options.number > 1
                        else output_name)
        latex_generator.context['NAME'] = name
        #~ filename = filename.replace(' ', '\ ')
        filenames.append(filename)

        # Output is redirected to a .log file
        sys.stdout = sys.stderr = CustomOutput((filename + '-python.log')
                                              if not options.remove else '')
        make_file(syntax_tree, filename, make_tex_file=make_tex, \
                    make_pdf_file=('pdf' in formats), options=options
                    )

    return filenames, output_name



def make_file(syntax_tree, output_name, make_tex_file=False,
                 make_pdf_file=True, options=None):
    remove = getattr(options, 'remove', False)
    quiet = getattr(options, 'quiet', False)

    dir_name = os.path.split(output_name)[0]
    extra = (('-output-directory "%s"' % dir_name) if dir_name else '')
    try:
        latex_generator.parse_node(syntax_tree)
    except Exception:
        print('\n*** Error occured while parsing. ***')
        print('This is current parser state for debugging purpose:')
        print(80*'-')
        print('... ' + ''.join(latex_generator.context['LATEX'][-10:]))
        print(80*'-')
        print('')
        raise
    latex = latex_generator.read()

    def compile_latex_file(filename):
        if quiet:
            command = param['quiet_tex_command']
        else:
            command = param['tex_command']
        command += ' %s "%s"' % (extra, filename)
        log = execute(command)
        # Run command twice if references were found.
        if 'Rerun to get cross-references right.' in log:
            log = execute(command)

    if make_tex_file:
        with open(output_name + '.tex', 'w') as texfile:
            texfile.write(latex)
            if make_pdf_file:
                texfile.flush()
                compile_latex_file(texfile.name)
                if remove:
                    for extension in ('aux', 'log', 'out'):
                        name = '%s.%s' % (output_name, extension)
                        if os.path.isfile(name):
                            os.remove(name)
    else:
        try:
            texfile = tempfile.NamedTemporaryFile(suffix='.tex')
            texfile.write(latex)
            if make_pdf_file:
                tmp_name  = os.path.split(texfile.name)[1][:-4] # without .tex extension
                tmp_names = {}
                output_names = {}
                for extension in ('pdf', 'log', 'aux', 'out'):
                    tmp_names[extension] = '%s.%s' % (tmp_name, extension)
                    output_names[extension] = '%s.%s' % (output_name, extension)
                texfile.flush()
                compile_latex_file(texfile.name)
                os.rename(tmp_names['pdf'], output_names['pdf'])
                for extension in ('log', 'aux', 'out'):
                    if os.path.isfile(tmp_names[extension]):
                        if remove:
                            os.remove(tmp_names[extension])
                        else:
                            os.rename(tmp_names[extension], output_names[extension])
        finally:
            texfile.close()



def join_files(output_name, filenames, formats, options):
    "Join different versions in a single pdf, then compress it if asked to."
    if options.compress or (options.cat and options.number > 1):
        # pdftk and ghostscript must be installed.
        if not ('pdf' in formats):
            print("Warning: --cat or --compress option meaningless if pdf output isn't selected.")
        else:
            filenames = [filename + '.pdf' for filename in filenames]
            pdf_name = output_name + '.pdf'
            if options.number > 1:
                files = ' '.join('"%s"' % filename for filename in filenames)
                print('Pdftk output:')
                print(execute('pdftk %s output "%s"' % (files, pdf_name)))
                if options.remove_all:
                    for name in filenames:
                        os.remove(name)
            if options.compress:
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
                temp_dir = tempfile.mkdtemp()
                pdf_with_seed = os.path.join(temp_dir, 'with_seed.pdf')
                execute('pdftk "%s" attach_files "%s" output "%s"' % (pdf_name, seed_file_name, pdf_with_seed))
                shutil.copyfile(pdf_with_seed, pdf_name)
    if options.reorder_pages:
        # Use pdftk to detect how many pages has the pdf document.
        n = int(execute('pdftk %s dump_data output | grep -i NumberOfPages:' % pdf_name).strip().split()[-1])
        mode = options.reorder_pages
        if mode == 'brochure':
            if n%4:
                raise RuntimeError, ('Page number is %s, but must be a multiple of 4.' % n)
            order = []
            for i in range(int(n/4)):
                order.extend([2*i + 1, 2*i + 2, n - 2*i - 1, n - 2*i])
        elif mode == 'brochure-reversed':
            if n%4:
                raise RuntimeError, ('Page number is %s, but must be a multiple of 4.' % n)
            order = n*[0]
            for i in range(int(n/4)):
                order[2*i] = 4*i + 1
                order[2*i + 1] = 4*i + 2
                order[n - 2*i - 2] = 4*i + 3
                order[n - 2*i - 1] = 4*i + 4
        else:
            raise NameError, ('Unknown mode %s for option --reorder-pages !' % mode)
        # monfichier.pdf -> monfichier-brochure.pdf
        new_name = '%s-%s.pdf' % (pdf_name[:pdf_name.index('.')], mode)
        execute('pdftk %s cat %s output %s' % (pdf_name, ' '.join(str(i) for i in order), new_name))
