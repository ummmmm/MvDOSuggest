import sublime, sublime_plugin
import re
import os.path

class MvDOSuggestCommand( sublime_plugin.EventListener ):
	def on_query_completions( self, view, prefix, locations ):
		if ( len( locations ) > 1 ): # do not allow multiple locations (selection points)
			return []
		elif not view.file_name().endswith( '.mv' ): # only add completions for *.mv files
			return []

		completions = []
		line		= view.substr( view.line( locations[ 0 ] ) )
		regex_mvdo	= re.compile( "\\[\\s*g\\.([^\\]]+)\\s*\\]\\." )
		result_mvdo	= regex_mvdo.search( line )
		root_path	= sublime.load_settings( 'mvdo_suggest.sublime-settings' ).get( "path" )

		if not result_mvdo:
			return []

		span_start, span_stop 		= result_mvdo.span()
		location_row, location_col	= view.rowcol( locations[ 0 ] )

		if span_stop + 1 != location_col: # ensures we only add completions if we are located at the start of an MvDO method
			if not re.search( '^[a-zA-Z0-9_]+$', line[ span_stop : location_col ] ): # look between the cursor pos, back to the MvDO to see if a method has been partially finished
				return []

		mv_file = self.lookup( result_mvdo.group( 1 ) )

		if mv_file is None: # failed to correlate the MvDO path
			return []

		for function in self.get_functions( root_path, mv_file ):
			completions.append( self.format_completion( function ) )

		return completions

	def format_completion( self, function ):
		params = ''

		if function[ 'params' ] == None or function[ 'params' ] == '':
			trigger 	= '{name}()'.format( name = function[ 'name' ] )
			contents	= trigger

			return ( trigger, contents )

		for index, param in enumerate( function[ 'params'].split( ',' ) ):
			if ( index > 0 ):
				params += ', '

			params += '${{{tab_index}:{text_output}}}'.format( tab_index = index + 1, text_output = param.strip() ) # literal { / } must be surrounded by { / } in order to escape properly

		trigger 	= '{name}( {params} )'.format( name = function[ 'name' ], params = function[ 'params' ] )
		contents	= '{name}( {params} )${{0}}'.format( name = function[ 'name' ], params = params ) # ending {0} is a literal value used for Sublime snippets

		return ( trigger, contents )

	def get_functions( self, root_path, mv_file ):
		mvfunctions 		= []
		mvincludes			= []
		mv_file				= os.path.join( os.path.abspath( root_path ), mv_file )
		regex_mvinclude 	= re.compile( "^<MvINCLUDE FILE = \"(.*\.mv)\">$" )
		regex_mvfunction	= re.compile( "^<MvFUNCTION NAME = \"([a-zA-Z0-9_]+)\"(?:\\s+PARAMETERS = \"([^\"]*)\")?" )

		if not os.path.isfile( mv_file ):
			print( "File not found {mv_file}".format( mv_file = mv_file ) )
			return []

		with open( mv_file, 'r' ) as f:
			for line in f:
				result_mvfunction = regex_mvfunction.search( line )

				if result_mvfunction:
					mvfunctions.append( { 'name' : result_mvfunction.group( 1 ), 'params' : result_mvfunction.group( 2 ).strip() if result_mvfunction.group( 2 ) else None } )
				else:
					result_mvinclude = regex_mvinclude.search( line )

					if result_mvinclude:
						mvincludes.append( result_mvinclude.group( 1 ) )

		for mvinclude in mvincludes:
			mvfunctions.extend( self.get_functions( root_path, mvinclude ) )

		return mvfunctions

	def lookup( self, key ):
		key 	= key.lower().strip()
		quick 	= self.quick_lookup( key )

		if quick:
			return quick

		regex_feature 	= re.compile( "^(?:module_)feature_(?:filename_)?([a-z]+)(?:_([a-z]+))?$" )
		regex_file		= re.compile( "^(?:module|filename)_([a-z]+)$" )
		result_feature	= regex_feature.search( key )

		if result_feature:
			if len( result_feature.groups() ):
				return 'features/{feature}/{feature}.mv'.format( feature = result_feature.group( 1 ) )

			return 'features/{feature}/{feature}_{file}.mv'.format( feature = result_feature.group( 1 ), file = result_feature.group( 2 ) )
		else:
			result_file = regex_file.search( key )

			if result_file:
				return '{file}.mv'.format( file = result_file.group( 1 ) )

		print( 'Failed to lookup MvDO path {key}'.format( key = key ) )

		return None

	def quick_lookup( self, key ):
		defaults = {}

		defaults[ 'module_admin' ]					= 'admin.mv'
		defaults[ 'filename_admin' ]				= 'admin.mv'

		defaults[ 'module_json' ]					= 'json.mv'
		defaults[ 'filename_json' ]					= 'json.mv'

		defaults[ 'library_db' ]					= 'lib/db.mv'
		defaults[ 'library_filename_db' ]			= 'lib/db.mv'
		defaults[ 'module_library_db' ]				= 'lib/db.mv'

		defaults[ 'library_dbapi' ]					= 'lib/dbapi.mv'
		defaults[ 'library_filename_dbapi' ]		= 'lib/dbapi.mv'
		defaults[ 'module_library_dbapi' ]			= 'lib/dbapi.mv'

		defaults[ 'library_native_dbapi' ]			= 'lib/dbapi_mysql.mv'
		defaults[ 'library_filename_native_dbapi' ]	= 'lib/dbapi_mysql.mv'
		defaults[ 'module_library_native_dbapi' ]	= 'lib/dbapi_mysql.mv'

		defaults[ 'library_utilities' ]				= 'lib/util.mv'
		defaults[ 'library_filename_utilities' ]	= 'lib/util.mv'
		defaults[ 'module_library_utilities' ]		= 'lib/util.mv'

		if key in defaults:
			return defaults[ key ]

		return None
