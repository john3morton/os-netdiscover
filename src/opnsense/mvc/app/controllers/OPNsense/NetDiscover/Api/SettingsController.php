<?php
namespace OPNsense\NetDiscover\Api;

use OPNsense\Base\ApiMutableModelControllerBase;

class SettingsController extends ApiMutableModelControllerBase
{
    protected static $internalModelClass = 'OPNsense\NetDiscover\NetDiscover';
    protected static $internalModelName  = 'netdiscover';

    public function setAction()
    {
        $result = parent::setAction();
        if ($result && isset($result['result']) && $result['result'] === 'saved') {
            $mdl = $this->getModel();
            $mdl->serializeToConfig();
            \OPNsense\Core\Config::getInstance()->save();
        }
        return $result;
    }
}
