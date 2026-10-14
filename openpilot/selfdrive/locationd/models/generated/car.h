#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_2545601134011040542);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8461508002424427576);
void car_H_mod_fun(double *state, double *out_704917235979003887);
void car_f_fun(double *state, double dt, double *out_237457952738950812);
void car_F_fun(double *state, double dt, double *out_4090080787877149803);
void car_h_25(double *state, double *unused, double *out_8286540641341237964);
void car_H_25(double *state, double *unused, double *out_2818063414010487790);
void car_h_24(double *state, double *unused, double *out_7115619409547049932);
void car_H_24(double *state, double *unused, double *out_6375989012812810926);
void car_h_30(double *state, double *unused, double *out_4004756236527653523);
void car_H_30(double *state, double *unused, double *out_1709632916117120408);
void car_h_26(double *state, double *unused, double *out_3430387197901047290);
void car_H_26(double *state, double *unused, double *out_923439904863568434);
void car_h_27(double *state, double *unused, double *out_5158530164707468007);
void car_H_27(double *state, double *unused, double *out_513961155066822809);
void car_h_29(double *state, double *unused, double *out_4791553227738343617);
void car_H_29(double *state, double *unused, double *out_1199401571802728224);
void car_h_28(double *state, double *unused, double *out_92112645989125284);
void car_H_28(double *state, double *unused, double *out_6281800588872258798);
void car_h_31(double *state, double *unused, double *out_8011346579056732075);
void car_H_31(double *state, double *unused, double *out_2848709375887448218);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}