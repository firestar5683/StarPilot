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
void car_err_fun(double *nom_x, double *delta_x, double *out_2228678220985197488);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4771042334963074054);
void car_H_mod_fun(double *state, double *out_6842308674734904229);
void car_f_fun(double *state, double dt, double *out_5170868391674818667);
void car_F_fun(double *state, double dt, double *out_608002520374966168);
void car_h_25(double *state, double *unused, double *out_5717488514750397721);
void car_H_25(double *state, double *unused, double *out_2411247173062410150);
void car_h_24(double *state, double *unused, double *out_3636388376143156521);
void car_H_24(double *state, double *unused, double *out_4636954957041278712);
void car_h_30(double *state, double *unused, double *out_1053346711599953215);
void car_H_30(double *state, double *unused, double *out_9118806559155524711);
void car_h_26(double *state, double *unused, double *out_6055019979260798860);
void car_H_26(double *state, double *unused, double *out_1330256145811646074);
void car_h_27(double *state, double *unused, double *out_8107069529503045581);
void car_H_27(double *state, double *unused, double *out_7153174202753601994);
void car_h_29(double *state, double *unused, double *out_3948326556060892430);
void car_H_29(double *state, double *unused, double *out_8608575214841132527);
void car_h_28(double *state, double *unused, double *out_9171930743130364298);
void car_H_28(double *state, double *unused, double *out_4755769841798888515);
void car_h_31(double *state, double *unused, double *out_5874675183101526866);
void car_H_31(double *state, double *unused, double *out_2441893134939370578);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}