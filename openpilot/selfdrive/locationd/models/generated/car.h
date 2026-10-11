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
void car_err_fun(double *nom_x, double *delta_x, double *out_5032200201446894984);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7143447445886649280);
void car_H_mod_fun(double *state, double *out_1685754253580569061);
void car_f_fun(double *state, double dt, double *out_8909179533363476452);
void car_F_fun(double *state, double dt, double *out_3419672683889849262);
void car_h_25(double *state, double *unused, double *out_5555793351249648290);
void car_H_25(double *state, double *unused, double *out_4322311178595995255);
void car_h_24(double *state, double *unused, double *out_8637534363345985562);
void car_H_24(double *state, double *unused, double *out_2909282930557586418);
void car_h_30(double *state, double *unused, double *out_5127685465639230885);
void car_H_30(double *state, double *unused, double *out_8850007508723603453);
void car_h_26(double *state, double *unused, double *out_4524369580962753368);
void car_H_26(double *state, double *unused, double *out_8063814497470051479);
void car_h_27(double *state, double *unused, double *out_3908981550453062561);
void car_H_27(double *state, double *unused, double *out_7421973253185523252);
void car_h_29(double *state, double *unused, double *out_3307563392839699007);
void car_H_29(double *state, double *unused, double *out_8339776164409211269);
void car_h_28(double *state, double *unused, double *out_8910654818113908206);
void car_H_28(double *state, double *unused, double *out_6376145892843885018);
void car_h_31(double *state, double *unused, double *out_357939675421100083);
void car_H_31(double *state, double *unused, double *out_8690022599703402955);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}