This are example NginX snippets.

Include these from your main config, example with

	include		/var/www/*/etc/nginx/*.conf;	

which means that you have done

	sudo ln -s --relative ../.. /var/www/vnc

