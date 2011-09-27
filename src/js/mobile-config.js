$(document).bind("mobileinit", function(){
$.mobile.defaultTransition = "slidedown";
$.mobile.ajaxLinksEnabled = false; // Ajax を使用したページ遷移を無効にする
$.mobile.ajaxFormsEnabled = false; // Ajax を使用したフォーム遷移を無効にする
$.mobile.ajaxEnabled = false; //Ajaxを使用禁止（falseに設定しないと、formで文字化け発生）
});

