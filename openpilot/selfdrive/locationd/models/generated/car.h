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
void car_err_fun(double *nom_x, double *delta_x, double *out_2901723881323854107);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2131234716339310483);
void car_H_mod_fun(double *state, double *out_796115697957996727);
void car_f_fun(double *state, double dt, double *out_1948741695251664277);
void car_F_fun(double *state, double dt, double *out_8655261788612512074);
void car_h_25(double *state, double *unused, double *out_3359435300487572769);
void car_H_25(double *state, double *unused, double *out_9161258703522981646);
void car_h_24(double *state, double *unused, double *out_6622515166733284665);
void car_H_24(double *state, double *unused, double *out_8316262094739286247);
void car_h_30(double *state, double *unused, double *out_411709310132087808);
void car_H_30(double *state, double *unused, double *out_2244568362031364891);
void car_h_26(double *state, double *unused, double *out_2192696010676609843);
void car_H_26(double *state, double *unused, double *out_5543982051312513746);
void car_h_27(double *state, double *unused, double *out_6396221351931905454);
void car_H_27(double *state, double *unused, double *out_4419331673831789802);
void car_h_29(double *state, double *unused, double *out_191606574544389709);
void car_H_29(double *state, double *unused, double *out_1734337017716972707);
void car_h_28(double *state, double *unused, double *out_293701916198711064);
void car_H_28(double *state, double *unused, double *out_7231650655938680207);
void car_h_31(double *state, double *unused, double *out_3411399925862778167);
void car_H_31(double *state, double *unused, double *out_9130612741646021218);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}