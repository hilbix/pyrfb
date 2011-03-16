<?
# $Header$
#
# Simple edit wrapper.
#
# $Log$
# Revision 1.1  2011/03/16 19:41:38  tino
# added
#

header("Content-type: text/plain");

$r = $_GET['r'];
if ($r=="dir" || $r=="gra")
  {
    $d = dir($r=="dir" ? 'e' : 'learn');
    while (false !== ($e=$d->read()))
      {
        if ($e=='.' || $e=='..') continue;
        echo htmlentities($e);
        echo "\n";
      }
  }
else
  die("wrong param r");
?>
